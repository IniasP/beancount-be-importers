from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount_be_importers.argenta import ArgentaImporter

FIXTURES = Path(__file__).parent / "fixtures"
importer = ArgentaImporter()


def test_identify_matches_only_argenta_fixture():
    assert importer.identify(str(FIXTURES / "argenta_sample.csv"))
    assert not importer.identify(str(FIXTURES / "belfius_sample.csv"))
    assert not importer.identify(str(FIXTURES / "degiro_sample.csv"))


def test_extract_sorts_and_maps():
    entries = importer.extract(str(FIXTURES / "argenta_sample.csv"), [])

    assert [e.date for e in entries] == [date(2024, 1, 10), date(2024, 1, 15)]

    salary, groceries = entries
    assert salary.payee == "WERKGEVER NV"
    assert salary.narration == "Loon januari"
    assert len(salary.postings) == 1
    assert salary.postings[0].account == "Assets:Argenta:Checking"
    assert salary.postings[0].units.currency == "EUR"
    assert salary.postings[0].units.number == Decimal("2500.00")

    assert groceries.payee == "ALBERT HEIJN 3010"
    assert groceries.narration == "Aankoop boodschappen"
    assert groceries.postings[0].units.number == Decimal("-45.67")


def test_blank_payee_falls_back_to_narration_only(tmp_path):
    csv_path = tmp_path / "blank_payee.csv"
    csv_path.write_text(
        "Verrichtingsdatum,Naam tegenpartij,Mededeling,Munt,Bedrag\n"
        "2024-02-01 12:00:00,,Own transfer,EUR,10.00\n",
        encoding="utf8",
    )

    (entry,) = importer.extract(str(csv_path), [])

    assert entry.payee is None
    assert entry.narration == "Own transfer"
