from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount_be_importers.belfius import BelfiusImporter

FIXTURES = Path(__file__).parent / "fixtures"
importer = BelfiusImporter()


def test_identify_matches_only_belfius_fixture():
    assert importer.identify(str(FIXTURES / "belfius_sample.csv"))
    assert not importer.identify(str(FIXTURES / "argenta_sample.csv"))
    assert not importer.identify(str(FIXTURES / "degiro_sample.csv"))


def test_extract_skips_preamble_sorts_and_maps():
    entries = importer.extract(str(FIXTURES / "belfius_sample.csv"), [])

    assert [e.date for e in entries] == [date(2024, 1, 10), date(2024, 1, 15)]

    salary, groceries = entries
    assert salary.payee == "WERKGEVER NV"
    assert salary.narration == "Loon januari"
    assert salary.postings[0].account == "Assets:Belfius:Checking"
    assert salary.postings[0].units.number == Decimal("2500.00")

    assert groceries.payee == "ALBERT HEIJN 3169 DIEST"
    assert groceries.postings[0].units.number == Decimal("-45.67")
