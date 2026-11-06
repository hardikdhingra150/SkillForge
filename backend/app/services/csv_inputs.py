import csv
import io
import re
from decimal import Decimal, InvalidOperation

MAX_BYTES = 1024 * 1024
MAX_ROWS = 10000
MAX_COLUMNS = 50


def parse_csv(content: bytes):
    if not content or len(content) > MAX_BYTES:
        raise ValueError("Upload a non-empty CSV no larger than 1 MiB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Save the CSV using UTF-8 encoding.") from None
    if "\x00" in text:
        raise ValueError("The file contains invalid null characters.")

    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        headers = next(reader, [])
        if not 2 <= len(headers) <= MAX_COLUMNS:
            raise ValueError("The CSV must have between 2 and 50 columns.")
        if any(not name.strip() or len(name) > 120 for name in headers):
            raise ValueError("Column headers must be non-empty and at most 120 characters.")
        if len(set(headers)) != len(headers):
            raise ValueError("The CSV has duplicate column headers.")

        rows = []
        for row in reader:
            if not row or all(not cell.strip() for cell in row):
                continue
            if len(row) != len(headers):
                raise ValueError(f"CSV line {reader.line_num} has the wrong number of columns.")
            if any(len(cell) > 5000 for cell in row):
                raise ValueError("A CSV cell exceeds 5,000 characters.")
            rows.append(row)
            if len(rows) > MAX_ROWS:
                raise ValueError("The CSV exceeds 10,000 data rows.")
    except csv.Error:
        raise ValueError("The CSV quoting or structure is invalid.") from None

    if not rows:
        raise ValueError("The CSV must contain at least one data row.")
    return headers, rows


CURRENCY_SYMBOLS = "$€£₹¥"
GROUPED = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
PLAIN = re.compile(r"^\d+(\.\d+)?$")


def parse_amount(text: str) -> Decimal:
    """Parse a money amount: plain decimals, or exports like $1,200.50, -€300 and (1,200).

    Thousands separators must group by three; anything ambiguous is rejected.
    """
    raw = text.strip()
    try:
        return Decimal(raw)
    except InvalidOperation:
        pass
    value, negative = raw, False
    if value.startswith("(") and value.endswith(")"):
        value, negative = value[1:-1].strip(), True
    if value.startswith("-"):
        value, negative = value[1:].strip(), not negative
    if value[:1] and value[0] in CURRENCY_SYMBOLS:
        value = value[1:].strip()
    if value.startswith("-") and not negative:
        value, negative = value[1:].strip(), True
    if not (GROUPED.match(value) or PLAIN.match(value)):
        raise InvalidOperation(raw)
    amount = Decimal(value.replace(",", ""))
    return -amount if negative else amount


def validate_mapping(headers, rows, product_column, revenue_column):
    if product_column not in headers or revenue_column not in headers:
        raise ValueError("Choose both columns from this file's headers.")
    if product_column == revenue_column:
        raise ValueError("Product and revenue must use different columns.")

    product_index = headers.index(product_column)
    revenue_index = headers.index(revenue_column)
    for row_number, row in enumerate(rows, start=1):
        if not row[product_index].strip():
            raise ValueError(f"The product value is empty on data row {row_number}.")
        try:
            number = parse_amount(row[revenue_index])
        except InvalidOperation:
            raise ValueError(f"The revenue value is not numeric on data row {row_number}.") from None
        if not number.is_finite() or number.adjusted() > 17 or number.as_tuple().exponent < -6:
            raise ValueError(
                f"Revenue on data row {row_number} must be finite, "
                "with at most 18 integer digits and 6 decimal places."
            )


MAX_XLSX_BYTES = 5 * 1024 * 1024
MAX_XLSX_UNPACKED = 80 * 1024 * 1024


def _cell_text(value) -> str:
    """An Excel cell as the text a CSV export would hold."""
    from datetime import date, datetime, time

    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, datetime):
        return value.date().isoformat() if value.time() == time(0) else value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)
    return str(value)


def xlsx_to_csv(content: bytes) -> bytes:
    """Convert the first worksheet of an .xlsx file to UTF-8 CSV bytes (values, not formulas).

    Guards against zip bombs before opening, and stops reading past the CSV row and column limits.
    """
    import zipfile

    if not content or len(content) > MAX_XLSX_BYTES:
        raise ValueError("Upload a non-empty Excel file no larger than 5 MiB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        if sum(item.file_size for item in archive.infolist()) > MAX_XLSX_UNPACKED:
            raise ValueError("The Excel file expands to too much data.")
    except zipfile.BadZipFile:
        raise ValueError("This is not a valid .xlsx file. Save it as Excel Workbook (.xlsx) or CSV.") from None

    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception:
        raise ValueError("The Excel file could not be read. Save it again as .xlsx or CSV.") from None
    try:
        sheet = workbook.worksheets[0]
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        width = None
        for index, row in enumerate(sheet.iter_rows(values_only=True)):
            cells = [_cell_text(value) for value in row]
            if width is None:
                while cells and not cells[-1].strip():
                    cells.pop()
                if not cells:
                    continue  # leading blank rows before the header
                width = len(cells)
                if width > MAX_COLUMNS:
                    raise ValueError("The sheet must have between 2 and 50 columns.")
            elif any(cell.strip() for cell in cells[width:]):
                raise ValueError(f"Row {index + 1} of the sheet has values outside the header's columns.")
            cells = (cells + [""] * width)[:width]
            writer.writerow(cells)
            if index > MAX_ROWS + 50:
                raise ValueError("The sheet exceeds 10,000 data rows.")
    finally:
        workbook.close()
    data = out.getvalue().encode()
    if len(data) > MAX_BYTES:
        raise ValueError("The sheet is larger than 1 MiB once converted to CSV.")
    return data
