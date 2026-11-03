import unittest
from types import SimpleNamespace

from app.sandbox import check_source, run_skill
from app.services.checks import CheckFailed
from app.services.repair import (
    STRATEGIES,
    Failure,
    NormalizeAmounts,
    classify_check,
    classify_run_error,
    decode_fixture,
    encode_fixture,
    failing_input_fixture,
    lineage_fixtures,
)
from app.services.skill_registry import run_fixture_tests
from app.skills import REVENUE_BY_PRODUCT, SALES_MAPPING

FORMATTED = b'Product,Sales\nPen,"$1,200.00"\nBook,$200\nPen,(50)\n'


class ClassifierTests(unittest.TestCase):
    def test_tool_errors_keep_their_code(self):
        failure = classify_run_error({"type": "ToolError", "code": "BAD_NUMBER", "message": "'$1' is not a plain number.",
                                      "details": {"value": "$1"}})
        self.assertEqual((failure.code, failure.details), ("BAD_NUMBER", {"value": "$1"}))

    def test_other_errors(self):
        self.assertEqual(classify_run_error({"type": "Timeout", "message": "slow"}).code, "TIMEOUT")
        self.assertEqual(classify_run_error({"type": "KeyError", "message": "x"}).code, "SKILL_ERROR")
        self.assertEqual(classify_check(CheckFailed("overall_total", "bad")).details, {"check": "overall_total"})


class NormalizeAmountsTests(unittest.TestCase):
    def setUp(self):
        self.strategy = NormalizeAmounts()
        self.failure = Failure("BAD_NUMBER", "'$1,200.00' is not a plain number.", {"value": "$1,200.00"})

    def test_v1_really_fails_on_exported_amounts(self):
        result = run_skill(REVENUE_BY_PRODUCT.source, inputs=SALES_MAPPING, files={"sales_csv": FORMATTED},
                           tools=REVENUE_BY_PRODUCT.contract["tools"])
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "BAD_NUMBER")

    def test_applies_only_to_bad_numbers_in_strict_skills(self):
        self.assertTrue(self.strategy.applies(self.failure, REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract))
        self.assertFalse(self.strategy.applies(Failure("MISSING_COLUMN", "x"), REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract))
        patched = self.strategy.patch(self.failure, REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract)
        self.assertFalse(self.strategy.applies(self.failure, patched.source, patched.contract), "must not re-apply")

    def test_patch_is_safe_minimal_and_proven(self):
        patch = self.strategy.patch(self.failure, REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract)
        check_source(patch.source)
        self.assertNotIn("to_decimal", patch.contract["tools"])
        self.assertIn("parse_amount", patch.contract["tools"])
        self.assertEqual(patch.source.count("parse_amount"), 1)
        # Built-in regression fixtures + the strategy's proof + the real failing input all pass.
        fixtures = REVENUE_BY_PRODUCT.fixtures + patch.fixtures + [failing_input_fixture("1.1.0", SALES_MAPPING, {"sales_csv": FORMATTED})]
        evidence = run_fixture_tests(patch.source, patch.contract, fixtures)
        self.assertEqual(evidence["test_count"], 6)
        result = run_skill(patch.source, inputs=SALES_MAPPING, files={"sales_csv": FORMATTED}, tools=patch.contract["tools"])
        self.assertEqual(result.output["total_revenue"], "1350.00")

    def test_strategy_registry_names_are_unique(self):
        names = [strategy.name for strategy in STRATEGIES]
        self.assertEqual(len(names), len(set(names)))


class FixtureLineageTests(unittest.TestCase):
    def test_fixtures_round_trip_through_json(self):
        item = encode_fixture("f", SALES_MAPPING, {"sales_csv": FORMATTED}, "checks")
        self.assertEqual(decode_fixture(item), ("f", SALES_MAPPING, {"sales_csv": FORMATTED}, "checks"))

    def test_large_inputs_are_not_stored_as_fixtures(self):
        self.assertIsNone(failing_input_fixture("1.1.0", {}, {"sales_csv": b"x" * (300 * 1024)}))

    def test_lineage_collects_builtin_and_every_ancestor_repair(self):
        v11 = SimpleNamespace(skill_id="revenue_by_product", version="1.1.0", parent_version="1.0.0",
                              change_json={"fixtures": [encode_fixture("a", {}, {"x": b"1"}, "checks")]})
        v12 = SimpleNamespace(skill_id="revenue_by_product", version="1.2.0", parent_version="1.1.0",
                              change_json={"fixtures": [encode_fixture("b", {}, {"x": b"2"}, "checks")]})
        v10 = SimpleNamespace(skill_id="revenue_by_product", version="1.0.0", parent_version=None, change_json=None)
        rows = {("revenue_by_product", "1.1.0"): v11, ("revenue_by_product", "1.0.0"): v10}
        db = SimpleNamespace(get=lambda _model, key: rows.get(key))
        names = [fixture[0] for fixture in lineage_fixtures(db, v12)]
        self.assertEqual(names[:4], [f[0] for f in REVENUE_BY_PRODUCT.fixtures])
        self.assertEqual(names[4:], ["b", "a"])


if __name__ == "__main__":
    unittest.main()
