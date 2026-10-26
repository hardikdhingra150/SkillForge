import unittest

from app.services.csv_inputs import MAX_BYTES, MAX_COLUMNS, MAX_ROWS, parse_csv, validate_mapping


class CSVInputTests(unittest.TestCase):
    def test_sample_preserves_headers_and_business_values(self):
        headers, rows = parse_csv(b"Product,Sales\nPen,100\nBook,200\nPen,50\n")
        self.assertEqual(headers, ["Product", "Sales"])
        self.assertEqual(rows, [["Pen", "100"], ["Book", "200"], ["Pen", "50"]])
        validate_mapping(headers, rows, "Product", "Sales")

    def test_bom_quoted_fields_and_blank_lines(self):
        headers, rows = parse_csv('\ufeffProduct,Sales\n"Pen, blue",100.00\n\n'.encode())
        self.assertEqual(headers, ["Product", "Sales"])
        self.assertEqual(rows, [["Pen, blue", "100.00"]])

    def test_rejects_invalid_encoding_nulls_empty_and_oversize(self):
        for content in (b"", b"Product,Sales\n", b"Product,Sales\n\xff,1", b"Product,Sales\nP\x00,1", b"x" * (MAX_BYTES + 1)):
            with self.subTest(content_length=len(content)):
                with self.assertRaises(ValueError):
                    parse_csv(content)

    def test_rejects_duplicate_blank_or_excess_headers(self):
        too_many = ",".join(f"col{i}" for i in range(MAX_COLUMNS + 1)).encode() + b"\n"
        for content in (b"Product,Product\nP,1", b"Product, \nP,1", b"Product\nP", too_many):
            with self.subTest(content=content[:60]):
                with self.assertRaises(ValueError):
                    parse_csv(content)

    def test_rejects_malformed_rows_and_quoting(self):
        for content in (b"Product,Sales\nP,1,extra", b"Product,Sales\nP", b'Product,Sales\n"unterminated,1'):
            with self.subTest(content=content):
                with self.assertRaises(ValueError):
                    parse_csv(content)

    def test_rejects_excess_rows_and_large_cells(self):
        for content in (b"Product,Sales\n" + b"P,1\n" * (MAX_ROWS + 1), b"Product,Sales\n" + b"P" * 5001 + b",1"):
            with self.subTest(content_length=len(content)):
                with self.assertRaises(ValueError):
                    parse_csv(content)

    def test_mapping_requires_distinct_existing_columns(self):
        for product, revenue in (("Product", "Product"), ("unknown", "Sales"), ("Product", "revenue")):
            with self.subTest(product=product, revenue=revenue):
                with self.assertRaises(ValueError):
                    validate_mapping(["Product", "Sales"], [["Pen", "100"]], product, revenue)

    def test_mapping_checks_every_row_for_numeric_revenue(self):
        for value in ("", "NaN", "Infinity", "-Infinity", "$100", "1,000", "1000000000000000000", "1.1234567"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_mapping(["Product", "Sales"], [["Pen", "100"], ["Book", value]], "Product", "Sales")

    def test_mapping_rejects_blank_products(self):
        with self.assertRaises(ValueError):
            validate_mapping(["Product", "Sales"], [[" ", "100"]], "Product", "Sales")

    def test_mapping_accepts_documented_numeric_boundaries(self):
        for value in ("999999999999999999", "1.123456", "-50", "0"):
            with self.subTest(value=value):
                validate_mapping(["Product", "Sales"], [["Pen", value]], "Product", "Sales")


if __name__ == "__main__":
    unittest.main()
