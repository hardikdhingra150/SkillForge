import copy
import unittest

from app.services.builtin_sales import run_sales, run_self_tests, validate_sales_result

CSV = b"Product,Sales\nPen,100\nBook,200\nPen,50\n"
MAPPING = {"product": "Product", "revenue": "Sales"}


class SalesTests(unittest.TestCase):
    def test_known_fixture(self):
        result = run_sales(CSV, MAPPING)
        totals = {item["product"]: item["revenue"] for item in result["products"]}
        self.assertEqual(totals, {"Book": "200", "Pen": "150"})
        self.assertEqual(result["total_revenue"], "350")
        self.assertEqual(result["rows_processed"], 3)

    def test_decimal_accuracy(self):
        result = run_sales(b"Product,Sales\nA,0.1\nA,0.2\n", MAPPING)
        self.assertEqual(result["total_revenue"], "0.3")

    def test_swapped_group_totals_are_rejected(self):
        result = run_sales(CSV, MAPPING)
        result["products"][0]["revenue"] = "150"
        result["products"][1]["revenue"] = "200"
        with self.assertRaises(ValueError):
            validate_sales_result(CSV, MAPPING, result)

    def test_duplicate_groups_are_rejected(self):
        result = run_sales(CSV, MAPPING)
        result["products"].append(copy.deepcopy(result["products"][0]))
        with self.assertRaises(ValueError):
            validate_sales_result(CSV, MAPPING, result)

    def test_self_tests(self):
        evidence = run_self_tests()
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["test_count"], 4)


if __name__ == "__main__":
    unittest.main()
