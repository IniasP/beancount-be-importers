from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from beancount_be_importers.degiro import DegiroImporter, extract_quantity_and_price, find_group_rows

FIXTURES = Path(__file__).parent / "fixtures"
importer = DegiroImporter(isin_mapping={"IE00BK5BQT80": "VWCE", "IE00B4L5Y983": "IWDA"})


def test_identify_matches_only_degiro_fixture():
    assert importer.identify(str(FIXTURES / "degiro_sample.csv"))
    assert not importer.identify(str(FIXTURES / "argenta_sample.csv"))
    assert not importer.identify(str(FIXTURES / "belfius_sample.csv"))


def test_extract_groups_full_purchase_with_fee_and_tax():
    entries = importer.extract(str(FIXTURES / "degiro_sample.csv"), [])

    full = next(e for e in entries if e.date == date(2024, 1, 15))
    assert full.narration == "Degiro"
    assert [(p.account, p.units.number, p.units.currency) for p in full.postings] == [
        ("Assets:Degiro:Cash", Decimal("-670.50"), "EUR"),
        ("Assets:Degiro:Cash", Decimal("-3.00"), "EUR"),
        ("Assets:Degiro:Cash", Decimal("-1.32"), "EUR"),
        ("Assets:Degiro:VWCE", Decimal("5"), "VWCE"),
        ("Expenses:Taxes:Investing", Decimal("1.32"), "EUR"),
        ("Expenses:Investing:Fees", Decimal("3.00"), "EUR"),
    ]
    commodity_posting = full.postings[3]
    assert commodity_posting.cost.number_per == Decimal("134.10")
    assert commodity_posting.cost.currency == "EUR"


def test_extract_omits_fee_and_tax_legs_when_absent():
    entries = importer.extract(str(FIXTURES / "degiro_sample.csv"), [])

    purchase_only = next(e for e in entries if e.date == date(2024, 1, 20))
    assert [(p.account, p.units.number) for p in purchase_only.postings] == [
        ("Assets:Degiro:Cash", Decimal("-151.00")),
        ("Assets:Degiro:IWDA", Decimal("2")),
    ]


def test_extract_quantity_and_price_handles_malformed_description():
    assert extract_quantity_and_price("Some unrelated transaction") == (0, Decimal("0"))
    assert extract_quantity_and_price("Koop rommel @ EUR") == (0, Decimal("0"))


def test_find_group_rows_raises_without_purchase():
    transactions = [
        {
            "Tijd": "10:00",
            "Omschrijving": "Transactiekosten en/of kosten van derden",
            "Mutatie_Amount": "-3,00",
        },
    ]
    with pytest.raises(ValueError):
        find_group_rows(transactions)
