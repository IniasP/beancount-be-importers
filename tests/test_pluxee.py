from datetime import date
from decimal import Decimal
from pathlib import Path

from beancount_be_importers.pluxee import (
    MaaltijdchequesImporter,
    EcochequeImporter,
)

FIXTURES = Path(__file__).parent / "fixtures"
maaltijdcheques_importer = MaaltijdchequesImporter()
ecocheque_importer = EcochequeImporter()


def test_identify_maaltijdcheques():
    assert maaltijdcheques_importer.identify(str(FIXTURES / "pluxee_sample.csv"))
    assert not maaltijdcheques_importer.identify(str(FIXTURES / "argenta_sample.csv"))
    assert not maaltijdcheques_importer.identify(str(FIXTURES / "belfius_sample.csv"))
    assert not maaltijdcheques_importer.identify(str(FIXTURES / "degiro_sample.csv"))


def test_extract_maaltijdcheques_maps_spend_and_topup():
    entries = maaltijdcheques_importer.extract(
        str(FIXTURES / "pluxee_sample.csv"), []
    )

    assert [e.date for e in entries] == [
        date(2024, 1, 10),
        date(2024, 1, 15),
        date(2024, 1, 20),
    ]

    topup, groceries, restaurant = entries

    assert topup.payee == "ACME"
    assert topup.narration == "Maaltijdcheques"
    assert topup.postings[0].account == "Assets:Pluxee:Maaltijdcheques"
    assert topup.postings[0].units.currency == "EUR"
    assert topup.postings[0].units.number == Decimal("40")

    assert groceries.payee == "ALBERT HEIJN 3010"
    assert groceries.narration == "ALBERT HEIJN 3010"
    assert groceries.postings[0].units.number == Decimal("-45.67")

    assert restaurant.payee == "NAOSHA DIEST"
    assert restaurant.narration == "NAOSHA DIEST"
    assert restaurant.postings[0].units.number == Decimal("-9.70")

    # Narration (not just payee) must differ per merchant: beancount-import's
    # classifier trains only on Posting.meta["source_desc"], which is copied
    # from narration, so a constant narration would give it nothing to learn
    # the Expenses: account from.
    assert groceries.narration != restaurant.narration


def test_identify_ecocheques():
    assert ecocheque_importer.identify(str(FIXTURES / "ecocheque_sample.csv"))
    assert not ecocheque_importer.identify(str(FIXTURES / "pluxee_sample.csv"))
    assert not ecocheque_importer.identify(str(FIXTURES / "argenta_sample.csv"))


def test_extract_ecocheques_maps_spend_and_topup():
    entries = ecocheque_importer.extract(str(FIXTURES / "ecocheque_sample.csv"), [])

    assert [e.date for e in entries] == [
        date(2024, 1, 5),
        date(2024, 1, 12),
        date(2024, 1, 20),
    ]

    topup, spend1, spend2 = entries

    assert topup.payee == "ACME"
    assert topup.narration == "Ecocheques"
    assert topup.postings[0].account == "Assets:Pluxee:Ecocheques"
    assert topup.postings[0].units.currency == "EUR"
    assert topup.postings[0].units.number == Decimal("250")

    assert spend1.payee == "COOLBLUE België Hasselt"
    assert spend1.narration == "COOLBLUE België Hasselt"
    assert spend1.postings[0].units.number == Decimal("-225.79")

    assert spend2.payee == "FLORALUX HAM Kwaadmechelen"
    assert spend2.postings[0].units.number == Decimal("-24.21")
