import copy
import unittest
from types import SimpleNamespace

from app.services.repair import encode_fixture
from app.services.skill_bundle import FORMAT, BundleError, export_bundle, import_bundle
from app.services.skill_registry import implementation_hash
from app.skills import REVENUE_BY_PRODUCT


class FakeDB:
    def __init__(self, existing=()):
        self.rows = list(existing)
        self.added = []

    def scalars(self, _query):
        return SimpleNamespace(all=lambda: self.rows)

    def add(self, row):
        self.added.append(row)

    def flush(self):
        pass


def bundle():
    source, contract = REVENUE_BY_PRODUCT.source, REVENUE_BY_PRODUCT.contract
    return {
        "format": FORMAT,
        "skill": {"skill_id": "revenue_by_product", "version": "1.0.0", "contract": contract, "source": source,
                  "implementation_hash": implementation_hash(source, contract), "origin": "builtin"},
        "fixtures": [encode_fixture(*f) for f in REVENUE_BY_PRODUCT.fixtures],
    }


class ExportTests(unittest.TestCase):
    def test_omits_recorded_inputs_but_keeps_builtin_fixtures(self):
        skill = SimpleNamespace(
            skill_id="revenue_by_product", version="1.0.0", capability="revenue_by_product",
            origin="repaired", parent_version=None, contract_json={}, source_code="source",
            implementation_hash="hash", validation_json={}, change_json={"fixtures": [
                encode_fixture("regression_input_for_v1.0.0", {}, {"sales_csv": b"private"}, "checks"),
            ]},
        )
        exported = export_bundle(FakeDB(), skill)
        self.assertEqual(len(exported["fixtures"]), len(REVENUE_BY_PRODUCT.fixtures))
        self.assertFalse(any(item["name"].startswith("regression_input_") for item in exported["fixtures"]))


class ImportTests(unittest.TestCase):
    def test_valid_bundle_is_reproven_and_stored_as_imported(self):
        db = FakeDB()
        row, created = import_bundle(db, bundle())
        self.assertTrue(created)
        self.assertEqual((row.origin, row.status, row.version), ("imported", "validated", "1.0.0"))
        self.assertEqual(row.validation_json["test_count"], 4)
        self.assertTrue(row.validation_json["imported"])

    def test_identical_existing_version_is_returned_not_duplicated(self):
        existing = SimpleNamespace(version="1.0.0", implementation_hash=bundle()["skill"]["implementation_hash"])
        row, created = import_bundle(FakeDB([existing]), bundle())
        self.assertFalse(created)
        self.assertIs(row, existing)

    def test_version_clash_gets_the_next_free_version(self):
        other = SimpleNamespace(version="1.0.0", implementation_hash="b" * 64)
        row, _ = import_bundle(FakeDB([other]), bundle())
        self.assertEqual(row.version, "1.1.0")

    def test_tampered_code_is_rejected(self):
        tampered = bundle()
        tampered["skill"]["source"] += "\n# edited\n"
        with self.assertRaisesRegex(BundleError, "hash"):
            import_bundle(FakeDB(), tampered)

    def test_unsafe_code_is_rejected_even_with_a_matching_hash(self):
        evil = bundle()
        evil["skill"]["source"] = "import os\n" + evil["skill"]["source"]
        evil["skill"]["implementation_hash"] = implementation_hash(evil["skill"]["source"], evil["skill"]["contract"])
        with self.assertRaises(ValueError):
            import_bundle(FakeDB(), evil)

    def test_fixtures_are_required_and_must_pass(self):
        empty = bundle()
        empty["fixtures"] = []
        with self.assertRaisesRegex(BundleError, "no fixtures"):
            import_bundle(FakeDB(), empty)
        lying = bundle()
        lying["fixtures"] = copy.deepcopy(lying["fixtures"])
        lying["fixtures"][0]["expected"] = {"totals": {"Book": "999", "Pen": "150"}, "total_revenue": "1149"}
        with self.assertRaises(ValueError):
            import_bundle(FakeDB(), lying)

    def test_not_a_bundle(self):
        with self.assertRaises(BundleError):
            import_bundle(FakeDB(), {"format": "something-else"})


if __name__ == "__main__":
    unittest.main()
