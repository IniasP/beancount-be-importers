"""Beangulp importers for Pluxee products (maaltijdcheques and ecocheques) CSV exports."""

import csv
import re

from beangulp.importers import csvbase

from beancount.core import data

DEFAULT_MAALTIJDCHEQUES_ACCOUNT = "Assets:Pluxee:Maaltijdcheques"
DEFAULT_ECOCHEQUES_ACCOUNT = "Assets:Pluxee:Ecocheques"

UITGAVE_RE = re.compile(r"^Uitgave (.+?) \(Transactie ")
# Top-up rows ("Storting van ... van <employer>" / "Versement de ... de <employer>").
STORTING_RE = re.compile(r"^(?:Storting|Versement)\b.*\b(?:van|de) (.+?)\s*$")


class SemicolonDialect(csv.excel):  # pylint: disable=too-few-public-methods
    delimiter = ";"


def _extract_employer(value):
    """Return the employer that topped up the card for a top-up row, else None."""
    match = STORTING_RE.match(value)
    return match.group(1) if match else None


def _extract_merchant(value):
    """Return the merchant name for an "Uitgave ..." (spend) row, else None."""
    match = UITGAVE_RE.match(value)
    return " ".join(match.group(1).split()) if match else None


class Payee(csvbase.Column):
    def parse(self, value):
        merchant = _extract_merchant(value)
        if merchant:
            return merchant
        return _extract_employer(value)


class NarrationBase(csvbase.Column):
    # The merchant name (not a fixed string) so beancount-import's classifier
    # has per-merchant text to train the Expenses: account prediction on --
    # it only sees Posting.meta["source_desc"], which is copied from this
    # narration, never from payee.
    topup_narration = None  # Override in subclass

    def parse(self, value):
        merchant = _extract_merchant(value)
        if merchant:
            return merchant
        if _extract_employer(value):
            return self.topup_narration
        return value


class MaaltijdchequesNarration(NarrationBase):
    topup_narration = "Maaltijdcheques"


class EcochequeNarration(NarrationBase):
    topup_narration = "Ecocheques"


class IsSpend(csvbase.Column):
    def parse(self, value):
        return _extract_merchant(value) is not None


class PluxeeBaseImporter(csvbase.Importer):  # pylint: disable=abstract-method
    """Base class for Pluxee product importers (maaltijdcheques, ecocheques)."""

    encoding = "utf-8-sig"
    dialect = SemicolonDialect
    date = csvbase.Date("Datum", "%d-%m-%Y")
    payee = Payee("Beschrijving")
    is_spend = IsSpend("Beschrijving")
    amount = csvbase.Amount("Bedrag", subs={r"[+€\s]": ""})

    default_account = None  # Override in subclass

    def __init__(self, account=None):
        super().__init__(account or self.default_account, "EUR")

    def finalize(self, txn, row):
        if row.is_spend:
            posting = txn.postings[0]
            units = data.Amount(-posting.units.number, posting.units.currency)
            txn = txn._replace(postings=[posting._replace(units=units)])
        return txn


class MaaltijdchequesImporter(PluxeeBaseImporter):
    """Importer for Pluxee meal vouchers (maaltijdcheques)."""

    default_account = DEFAULT_MAALTIJDCHEQUES_ACCOUNT
    encoding = "utf-8-sig"
    dialect = SemicolonDialect
    date = csvbase.Date("Datum", "%d-%m-%Y")
    payee = Payee("Beschrijving")
    narration = MaaltijdchequesNarration("Beschrijving")
    is_spend = IsSpend("Beschrijving")
    amount = csvbase.Amount("Bedrag", subs={r"[+€\s]": ""})

    def identify(self, filepath):
        if not filepath.endswith(".csv"):
            return False
        with open(filepath, encoding="utf-8-sig") as file:
            content = file.read()
        # Must have proper header
        if "Beschrijving" not in content or "Bedrag" not in content:
            return False
        # Maaltijdcheques is for anything that's not eECO Pass
        # (could have eLunch Pass, Maaltijdcheques, Storting, etc.)
        return "eECO Pass" not in content


class EcochequeImporter(PluxeeBaseImporter):
    """Importer for Pluxee eco-cheques (ecocheques)."""

    default_account = DEFAULT_ECOCHEQUES_ACCOUNT
    encoding = "utf-8-sig"
    dialect = SemicolonDialect
    date = csvbase.Date("Datum", "%d-%m-%Y")
    payee = Payee("Beschrijving")
    narration = EcochequeNarration("Beschrijving")
    is_spend = IsSpend("Beschrijving")
    amount = csvbase.Amount("Bedrag", subs={r"[+€\s]": ""})

    def identify(self, filepath):
        if not filepath.endswith(".csv"):
            return False
        with open(filepath, encoding="utf-8-sig") as file:
            content = file.read()
        # Must have proper header
        if "Beschrijving" not in content or "Bedrag" not in content:
            return False
        # Ecocheques is for anything that contains eECO Pass
        return "eECO Pass" in content
