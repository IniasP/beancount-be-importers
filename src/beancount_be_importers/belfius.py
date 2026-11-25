"""Beangulp importer for Belfius checking-account CSV exports."""

import csv

from beangulp.importers import csvbase

HEADER_PREFIX = "Rekening;Boekingsdatum;"
DEFAULT_ACCOUNT = "Assets:Belfius:Checking"


# pylint: disable=duplicate-code
# Intentionally duplicated in argenta.py: each importer stays self-contained.
def normalize(text: str) -> str:
    return " ".join(text.split()).replace('"', "'")


class Narration(csvbase.Column):
    def parse(self, value):
        return normalize(value)


class Payee(csvbase.Column):
    def parse(self, value):
        return normalize(value) or None
# pylint: enable=duplicate-code


class SemicolonDialect(csv.excel):  # pylint: disable=too-few-public-methods
    delimiter = ";"


def _find_header_line(filepath) -> int:
    with open(filepath, encoding="utf8") as file:
        for lineno, line in enumerate(file):
            if line.startswith(HEADER_PREFIX):
                return lineno
    raise ValueError(f"No Belfius header line found in {filepath}")


class BelfiusImporter(csvbase.Importer):
    date = csvbase.Date("Boekingsdatum", "%d/%m/%Y")
    payee = Payee("Naam tegenpartij bevat")
    narration = Narration("Mededelingen")
    amount = csvbase.Amount("Bedrag", subs={",": "."})
    dialect = SemicolonDialect

    def __init__(self, account=DEFAULT_ACCOUNT, currency="EUR"):
        super().__init__(account, currency)

    def identify(self, filepath):
        if not filepath.endswith(".csv"):
            return False
        try:
            _find_header_line(filepath)
        except ValueError:
            return False
        return True

    def read(self, filepath):
        self.skiplines = _find_header_line(filepath)
        yield from super().read(filepath)
