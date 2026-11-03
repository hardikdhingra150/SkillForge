import copy
import unittest
from types import SimpleNamespace

from pydantic import ValidationError

from app.sandbox import run_skill
from app.schemas.skill_contract import SkillContract
from app.services.checks import CheckFailed, run_checks
from app.services.execution_queue import bind_inputs
from app.services.skill_registry import implementation_hash, run_fixture_tests, version_key
from app.skills import REVENUE_BY_PRODUCT, SALES_MAPPING

CSV = b"Product,Sales\nPen,100\nBook,200\nPen,50\n"
CONTRACT = SkillContract.model_validate(REVENUE_BY_PRODUCT.contract)


def run_sales(content, inputs=SALES_MAPPING):
    result = run_skill(REVENUE_BY_PRODUCT.source, inputs=inputs, files={"sales_csv": content}, tools=CONTRACT.tools)
    if not result.ok:
        raise AssertionError(result.error)
    return result.output


class SalesSkillTests(unittest.TestCase):
    def test_known_fixture(self):
        result = run_sales(CSV)
        totals = {item["product"]: item["revenue"] for item in result["products"]}
        self.assertEqual(totals, {"Book": "200", "Pen": "150"})
        self.assertEqual(result["total_revenue"], "350")
        self.assertEqual(result["rows_processed"], 3)
        self.assertEqual(run_checks(CONTRACT, {"sales_csv": CSV}, SALES_MAPPING, result)["passed"], True)

    def test_decimal_accuracy(self):
        self.assertEqual(run_sales(b"Product,Sales\nA,0.1\nA,0.2\n")["total_revenue"], "0.3")

    def test_swapped_group_totals_are_rejected(self):
        result = run_sales(CSV)
        result["products"][0]["revenue"] = "150"
        result["products"][1]["revenue"] = "200"
        with self.assertRaises(CheckFailed) as caught:
            run_checks(CONTRACT, {"sales_csv": CSV}, SALES_MAPPING, result)
        self.assertEqual(caught.exception.check, "per_product_totals")

    def test_duplicate_groups_are_rejected(self):
        result = run_sales(CSV)
        result["products"].append(copy.deepcopy(result["products"][0]))
        with self.assertRaises(CheckFailed):
            run_checks(CONTRACT, {"sales_csv": CSV}, SALES_MAPPING, result)

    def test_missing_output_fails_the_contract(self):
        result = run_sales(CSV)
        del result["total_revenue"]
        with self.assertRaises(CheckFailed) as caught:
            run_checks(CONTRACT, {"sales_csv": CSV}, SALES_MAPPING, result)
        self.assertEqual(caught.exception.check, "contract_outputs")

    def test_wrong_column_mapping_fails_in_the_sandbox(self):
        result = run_skill(REVENUE_BY_PRODUCT.source, inputs={"product_column": "Product", "revenue_column": "revenue"},
                           files={"sales_csv": CSV}, tools=CONTRACT.tools)
        self.assertFalse(result.ok)
        self.assertIn("Column 'revenue' not found", result.error["message"])

    def test_registration_fixtures_run_in_the_sandbox(self):
        evidence = run_fixture_tests(REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract, REVENUE_BY_PRODUCT.fixtures)
        self.assertTrue(evidence["passed"])
        self.assertEqual(evidence["test_count"], 4)
        self.assertEqual(evidence["runner"], "sandbox")


class RegistryHelperTests(unittest.TestCase):
    def test_hash_covers_source_and_contract(self):
        base = implementation_hash(REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract)
        self.assertEqual(base, implementation_hash(REVENUE_BY_PRODUCT.source, dict(reversed(REVENUE_BY_PRODUCT.contract.items()))))
        self.assertNotEqual(base, implementation_hash(REVENUE_BY_PRODUCT.source + "\n", REVENUE_BY_PRODUCT.contract))
        changed = {**REVENUE_BY_PRODUCT.contract, "summary": "Different."}
        self.assertNotEqual(base, implementation_hash(REVENUE_BY_PRODUCT.source, changed))

    def test_versions_sort_numerically(self):
        self.assertEqual(max(["1.9.0", "1.10.0", "1.2.0"], key=version_key), "1.10.0")

    def test_contract_rejects_unapproved_tools_and_unknown_checks(self):
        for patch in ({"tools": ["read_csv", "shell"]}, {"checks": ["trust_me"]}, {"capability": "Bad Name"}):
            with self.subTest(patch=patch), self.assertRaises(ValidationError):
                SkillContract.model_validate({**REVENUE_BY_PRODUCT.contract, **patch})

    def test_bind_inputs_maps_confirmed_columns(self):
        item = SimpleNamespace(content_bytes=CSV, mapping_json={"product": "Product", "revenue": "Sales"})
        inputs, files = bind_inputs(CONTRACT, item)
        self.assertEqual(inputs, SALES_MAPPING)
        self.assertEqual(files, {"sales_csv": CSV})

    def test_bind_inputs_requires_every_column(self):
        item = SimpleNamespace(content_bytes=CSV, mapping_json={"product": "Product"})
        with self.assertRaises(ValueError):
            bind_inputs(CONTRACT, item)


if __name__ == "__main__":
    unittest.main()
