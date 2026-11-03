import unittest

from app.sandbox import PolicyViolation, check_source, run_skill


def skill(body: str) -> str:
    return "def run(inputs, tools):\n" + "".join(f"    {line}\n" for line in body.splitlines())


class PolicyTests(unittest.TestCase):
    def assert_blocked(self, source, fragment):
        with self.assertRaises(PolicyViolation) as caught:
            check_source(source)
        self.assertIn(fragment, str(caught.exception))

    def test_blocks_imports(self):
        self.assert_blocked("import os\n" + skill("return {}"), "Import")
        self.assert_blocked("from pathlib import Path\n" + skill("return {}"), "ImportFrom")

    def test_blocks_dangerous_names(self):
        for name in ("open('x')", "eval('1')", "__import__('os')", "getattr(tools, 'x')", "globals()"):
            with self.subTest(name=name):
                self.assert_blocked(skill(f"return {name}"), "not allowed")

    def test_blocks_dunder_escapes(self):
        self.assert_blocked(skill("return ().__class__.__bases__"), "Private attribute")
        self.assert_blocked(skill("return tools._secret"), "Private attribute")

    def test_blocks_code_running_at_import(self):
        self.assert_blocked("x = [1]\n" + skill("return {}"), "module level")
        self.assert_blocked("class A:\n    pass\n" + skill("return {}"), "ClassDef")

    def test_requires_entrypoint_signature(self):
        self.assert_blocked("def main(inputs, tools):\n    return {}\n", "must define run")
        self.assert_blocked("def run(inputs):\n    return {}\n", "exactly (inputs, tools)")

    def test_rejects_syntax_errors_and_empty_source(self):
        self.assert_blocked("def run(inputs, tools)\n    return {}", "syntax error")
        self.assert_blocked("   ", "empty")


class RunnerTests(unittest.TestCase):
    def test_runs_with_granted_tools_only(self):
        result = run_skill(
            skill("h, rows = tools.read_csv('f')\nreturn {'n': len(rows)}"),
            inputs={}, files={"f": b"a,b\nx,1\ny,2\n"}, tools=["read_csv"],
        )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output, {"n": 2})

    def test_ungranted_tool_names_the_contract(self):
        result = run_skill(skill("return tools.read_csv('f')"), inputs={}, files={}, tools=[])
        self.assertFalse(result.ok)
        self.assertIn("not in this skill's contract", result.error["message"])

    def test_missing_column_lists_available_headers(self):
        result = run_skill(
            skill("h, r = tools.read_csv('f')\nreturn {'v': tools.column(h, r, 'revenue')}"),
            inputs={}, files={"f": b"Product,Sales\nA,1\n"}, tools=["read_csv", "column"],
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "MISSING_COLUMN")
        self.assertEqual(result.error["details"], {"column": "revenue", "available": ["Product", "Sales"]})
        self.assertIn("Available columns: Product, Sales", result.error["message"])

    def test_bad_number_carries_a_code_and_parse_amount_handles_exports(self):
        files = {"f": b"P,S\nA,$1,200.50\n".replace(b"$1,200.50", b'"$1,200.50"')}
        strict = run_skill(skill("h, r = tools.read_csv('f')\nreturn {'v': str(tools.to_decimal(tools.column(h, r, 'S')[0]))}"),
                           inputs={}, files=files, tools=["read_csv", "column", "to_decimal"])
        self.assertEqual((strict.error["code"], strict.error["details"]), ("BAD_NUMBER", {"value": "$1,200.50"}))
        lenient = run_skill(skill("h, r = tools.read_csv('f')\nreturn {'v': str(tools.parse_amount(tools.column(h, r, 'S')[0]))}"),
                            inputs={}, files=files, tools=["read_csv", "column", "parse_amount"])
        self.assertEqual(lenient.output, {"v": "1200.50"})

    def test_infinite_loop_times_out(self):
        result = run_skill(skill("while True:\n    pass"), inputs={}, files={}, tools=[], timeout=1.5)
        self.assertFalse(result.ok)
        self.assertEqual(result.error["type"], "Timeout")

    def test_output_must_be_a_json_dict(self):
        self.assertEqual(run_skill(skill("return [1]"), inputs={}, files={}, tools=[]).error["type"], "TypeError")
        self.assertFalse(run_skill(skill("return {'x': float('nan')}"), inputs={}, files={}, tools=[]).ok)

    def test_policy_violation_never_starts_a_process(self):
        with self.assertRaises(PolicyViolation):
            run_skill("import os\n" + skill("return {}"), inputs={}, files={}, tools=[])


if __name__ == "__main__":
    unittest.main()
