import csv
import io
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
            number = Decimal(row[revenue_index].strip())
        except InvalidOperation:
            raise ValueError(f"The revenue value is not numeric on data row {row_number}.") from None
        if not number.is_finite() or number.adjusted() > 17 or number.as_tuple().exponent < -6:
            raise ValueError(
                f"Revenue on data row {row_number} must be finite, "
                "with at most 18 integer digits and 6 decimal places."
            )
