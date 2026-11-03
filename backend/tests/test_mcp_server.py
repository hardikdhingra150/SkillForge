import unittest
from types import SimpleNamespace

from app.mcp_server import describe, input_schema, tool_name
from app.skills import REVENUE_BY_PRODUCT, STARTER_SKILLS


class McpSchemaTests(unittest.TestCase):
    def test_tool_names_are_mcp_safe(self):
        self.assertEqual(tool_name("revenue_by_product"), "revenue_by_product")
        self.assertEqual(tool_name("weird name!"), "weird_name_")
        self.assertLessEqual(len(tool_name("x" * 100)), 64)

    def test_csv_inputs_become_strings_and_required_fields_are_listed(self):
        schema = input_schema(REVENUE_BY_PRODUCT.contract)
        self.assertEqual(schema["properties"]["sales_csv"]["type"], "string")
        self.assertIn("CSV text", schema["properties"]["sales_csv"]["description"])
        self.assertEqual(schema["required"], ["sales_csv", "product_column", "revenue_column"])
        self.assertFalse(schema["additionalProperties"])

    def test_optional_inputs_are_not_required(self):
        dedupe = next(s for s in STARTER_SKILLS if s.skill_id == "dedupe_list")
        schema = input_schema(dedupe.contract)
        self.assertEqual(schema["required"], ["items"])
        self.assertEqual(schema["properties"]["items"]["type"], "array")
        self.assertEqual(schema["properties"]["case_sensitive"]["type"], "boolean")

    def test_description_carries_version_and_evidence(self):
        row = SimpleNamespace(contract_json={"summary": "Sum things."}, capability="sum", skill_id="sum", version="1.1.0",
                              origin="repaired", parent_version="1.0.0", validation_json={"test_count": 6})
        text = describe(row)
        self.assertIn("v1.1.0", text)
        self.assertIn("repaired from v1.0.0", text)
        self.assertIn("6 tests", text)


if __name__ == "__main__":
    unittest.main()
