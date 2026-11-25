"""Beangulp importer for Degiro Account.csv exports.

Groups the CSV's per-line-item transactions (purchase, fee, tax) by "Order Id"
into a single multi-posting Transaction, matching the shape already used in
a typical ledger. Deposits, interest, and connection fees have no Order Id and
are not handled here.

Commodity naming is configurable: pass ``isin_mapping`` ({ISIN: ticker}) to map ISINs
to the commodity names used in your ledger; unmapped ISINs are used as-is.
"""

import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import beangulp
from beancount.core import data
from beancount.core.amount import Amount

DEGIRO_DATE_FORMAT = "%d-%m-%Y"
DEFAULT_CASH_ACCOUNT = "Assets:Degiro:Cash"
DEFAULT_HOLDINGS_PREFIX = "Assets:Degiro"
DEFAULT_TAX_ACCOUNT = "Expenses:Taxes:Investing"
DEFAULT_FEE_ACCOUNT = "Expenses:Investing:Fees"

FIELDNAMES = [
    "Datum", "Tijd", "Valutadatum", "Product", "ISIN", "Omschrijving",
    "FX", "Mutatie_Currency", "Mutatie_Amount", "Saldo_Currency",
    "Saldo_Amount", "Order Id",
]


def parse_decimal(string: str) -> Decimal:
    if not string or not string.strip():
        return Decimal("0")
    return Decimal(string.strip('"').replace(",", "."))


def parse_date(date_str: str):
    return datetime.strptime(date_str, DEGIRO_DATE_FORMAT).date()


def extract_quantity_and_price(description: str) -> tuple[int, Decimal]:
    """Extract quantity and price from a description like 'Koop 5 @ 134,1 EUR'."""
    if "Koop" not in description or "@" not in description:
        return (0, Decimal("0"))
    try:
        parts = description.split("@")
        quantity = int(parts[0].replace("Koop", "").strip())
        price = parse_decimal(parts[1].replace("EUR", "").strip())
        return (quantity, price)
    except (ValueError, IndexError):
        return (0, Decimal("0"))


def group_transactions_by_order(rows: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for row in rows:
        order_id = (row.get("Order Id") or "").strip()
        if order_id:
            grouped[order_id].append(row)
    return grouped


def find_group_rows(transactions: list[dict]):
    """Split a group into its purchase/fee/tax rows (fee and tax are optional)."""
    transactions = sorted(transactions, key=lambda t: t.get("Tijd", ""))

    purchase_tx = fee_tx = tax_tx = None
    for tx in transactions:
        desc = tx.get("Omschrijving", "")
        if "Koop" in desc and "@" in desc:
            purchase_tx = tx
        elif "Transactiekosten" in desc or "kosten van derden" in desc:
            fee_tx = tx
        elif "Transactiebelasting" in desc:
            tax_tx = tx

    if purchase_tx is None:
        raise ValueError("No purchase transaction found in Degiro order group")

    return purchase_tx, fee_tx, tax_tx


def build_transaction(  # pylint: disable=too-many-locals
    transactions: list[dict], isin_mapping: dict, meta, accounts: dict
):
    purchase_tx, fee_tx, tax_tx = find_group_rows(transactions)

    entry_date = parse_date(purchase_tx["Datum"])
    isin = purchase_tx.get("ISIN", "")
    commodity = isin_mapping.get(isin, isin)
    quantity, price = extract_quantity_and_price(purchase_tx["Omschrijving"])
    purchase_amount = abs(parse_decimal(purchase_tx.get("Mutatie_Amount", "")))

    postings = [
        data.Posting(accounts["cash"], Amount(-purchase_amount, "EUR"), None, None, None, None),
    ]

    fee_amount = tax_amount = Decimal("0")
    if fee_tx is not None:
        fee_amount = abs(parse_decimal(fee_tx.get("Mutatie_Amount", "")))
        postings.append(data.Posting(accounts["cash"], Amount(-fee_amount, "EUR"), None, None, None, None))
    if tax_tx is not None:
        tax_amount = abs(parse_decimal(tax_tx.get("Mutatie_Amount", "")))
        postings.append(data.Posting(accounts["cash"], Amount(-tax_amount, "EUR"), None, None, None, None))

    cost = data.CostSpec(price, None, "EUR", None, None, False)
    postings.append(
        data.Posting(
            f'{accounts["holdings_prefix"]}:{commodity}',
            Amount(Decimal(quantity), commodity), cost, None, None, None,
        )
    )
    if tax_tx is not None:
        postings.append(
            data.Posting(accounts["tax"], Amount(tax_amount, "EUR"), None, None, None, None)
        )
    if fee_tx is not None:
        postings.append(
            data.Posting(accounts["fee"], Amount(fee_amount, "EUR"), None, None, None, None)
        )

    return data.Transaction(meta, entry_date, "*", None, "Degiro", data.EMPTY_SET, data.EMPTY_SET, postings)


class DegiroImporter(beangulp.Importer):
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def __init__(
        self,
        isin_mapping=None,
        cash_account=DEFAULT_CASH_ACCOUNT,
        holdings_prefix=DEFAULT_HOLDINGS_PREFIX,
        tax_account=DEFAULT_TAX_ACCOUNT,
        fee_account=DEFAULT_FEE_ACCOUNT,
    ):
        self.isin_mapping = dict(isin_mapping or {})
        self.cash_account = cash_account
        self._accounts = {
            "cash": cash_account,
            "holdings_prefix": holdings_prefix,
            "tax": tax_account,
            "fee": fee_account,
        }

    def identify(self, filepath):
        if not filepath.endswith(".csv"):
            return False
        with open(filepath, encoding="utf8") as file:
            header = file.readline()
        return "Order Id" in header

    def account(self, filepath):
        return self.cash_account

    def _read_groups(self, filepath):
        with open(filepath, encoding="utf8") as file:
            file.readline()
            reader = csv.DictReader(file, fieldnames=FIELDNAMES)
            rows = list(reader)
        return group_transactions_by_order(rows)

    def date(self, filepath):
        groups = self._read_groups(filepath)
        dates = [
            parse_date(find_group_rows(transactions)[0]["Datum"])
            for transactions in groups.values()
        ]
        return max(dates) if dates else None

    def extract(self, filepath, existing):
        entries = []
        for lineno, transactions in enumerate(self._read_groups(filepath).values()):
            meta = data.new_metadata(filepath, lineno)
            entries.append(build_transaction(transactions, self.isin_mapping, meta, self._accounts))
        return entries
