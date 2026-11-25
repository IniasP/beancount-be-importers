from os import path
import csv
import openpyxl

def xlsx_to_csv(file_path: str) -> str:
    """Convert xlsx/ods file to csv file, returning the csv file path"""
    file_name, file_extension = path.splitext(file_path)

    if file_extension == ".xlsx":
        csv_path = file_name + ".csv"

        # Load the workbook and get the active sheet
        workbook = openpyxl.load_workbook(file_path, data_only=True)
        sheet = workbook.active

        if sheet is None:
            raise ValueError(f"No active sheet found in {file_path}")

        # Write to CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as csv_file:
            csv_writer = csv.writer(csv_file)
            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                if any(cell is not None for cell in row):
                    csv_writer.writerow(row)

        workbook.close()
        return csv_path
    if file_extension == ".csv":
        return file_path
    raise ValueError(f"Unsupported file extension: cannot convert {file_extension} to csv")
