import csv

import openpyxl
import pytest

from beancount_be_importers.xlsx_to_csv import xlsx_to_csv


def test_xlsx_to_csv_converts_and_skips_empty_rows(tmp_path):
    xlsx_path = tmp_path / "sample.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["date", "amount"])
    sheet.append([None, None])
    sheet.append(["2024-01-01", 42])
    workbook.save(xlsx_path)

    csv_path = xlsx_to_csv(str(xlsx_path))

    assert csv_path == str(tmp_path / "sample.csv")
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows == [["date", "amount"], ["2024-01-01", "42"]]


def test_xlsx_to_csv_passthrough_for_csv():
    assert xlsx_to_csv("already.csv") == "already.csv"


def test_xlsx_to_csv_rejects_unsupported_extension():
    with pytest.raises(ValueError):
        xlsx_to_csv("file.txt")
