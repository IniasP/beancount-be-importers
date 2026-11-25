"""Beangulp importer for Argenta checking-account CSV/XLSX exports."""

from beangulp.importers import csvbase

from .xlsx_to_csv import xlsx_to_csv

DEFAULT_ACCOUNT = "Assets:Argenta:Checking"


# pylint: disable=duplicate-code
# Intentionally duplicated in belfius.py: each importer stays self-contained.
def normalize(text: str) -> str:
    return " ".join(text.split()).replace('"', "'")


class Narration(csvbase.Column):
    def parse(self, value):
        return normalize(value)


class Payee(csvbase.Column):
    def parse(self, value):
        return normalize(value) or None
# pylint: enable=duplicate-code


class ArgentaImporter(csvbase.Importer):
    date = csvbase.Date("Verrichtingsdatum", "%Y-%m-%d %H:%M:%S")
    payee = Payee("Naam tegenpartij")
    narration = Narration("Mededeling")
    amount = csvbase.Amount("Bedrag", subs={",": ""})

    def __init__(self, account=DEFAULT_ACCOUNT, currency="EUR"):
        super().__init__(account, currency)

    def identify(self, filepath):
        if filepath.endswith(".xlsx"):
            return True
        if not filepath.endswith(".csv"):
            return False
        with open(filepath, encoding="utf8") as file:
            header = file.readline()
        return "Verrichtingsdatum" in header and "Naam tegenpartij" in header

    def read(self, filepath):
        yield from super().read(xlsx_to_csv(filepath))
