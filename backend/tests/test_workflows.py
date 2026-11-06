import io
import unittest

from openpyxl import Workbook

from app.sandbox import run_skill
from app.sandbox.tools import ToolError, parse_dates, resolve_column
from app.services.csv_inputs import parse_csv, xlsx_to_csv
from app.services.repair import STRATEGIES, Failure, MatchColumnsLoosely, NormalizeDates, failing_input_fixture
from app.services.requirement_review import review_requirement
from app.services.skill_registry import run_fixture_tests
from app.services.workflows import WORKFLOWS, match_workflows, suggest_mapping, validate_columns
from app.skills import BUILTIN_SKILLS, FILE_SKILLS

SKILLS = {skill.skill_id: skill for skill in BUILTIN_SKILLS}


class MatchingTests(unittest.TestCase):
    def test_each_example_routes_to_its_workflow(self):
        for workflow in WORKFLOWS.values():
            with self.subTest(workflow=workflow.id):
                self.assertEqual(match_workflows(workflow.example), [workflow.id])
                self.assertEqual(review_requirement(workflow.example).candidate_workflow, workflow.id)

    def test_other_wording(self):
        cases = {"sum of spend per department": "totals_by_group", "Revenue by month please": "totals_by_month",
                 "deduplicate this list": "dedupe_rows", "tidy up the csv": "clean_table"}
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(match_workflows(text), [expected])

    def test_unclear_or_combined_requests_need_clarifying(self):
        for text in ("Show revenue by product and region", "forecast sales by region", "write me a poem"):
            with self.subTest(text=text):
                self.assertEqual(review_requirement(text).next_action, "clarify_requirement")

    def test_every_workflow_has_a_matching_skill(self):
        for workflow in WORKFLOWS.values():
            skill = SKILLS[workflow.id]
            columns = {f["name"].removesuffix("_column") for f in skill.contract["inputs"] if f["type"] == "column"}
            self.assertEqual(columns, {role.name for role in workflow.roles})


class SuggestionTests(unittest.TestCase):
    HEADERS = ["Order ID", "Order Date", "Region", "Item", "Total"]
    ROWS = [["1", "2026-01-03", "North", "Pen", "$1,200.00"], ["2", "03/02/2026", "South", "Ink", "(5)"]]

    def test_suggests_by_name_and_content(self):
        self.assertEqual(suggest_mapping("revenue_by_product", self.HEADERS, self.ROWS), {"product": "Item", "revenue": "Total"})
        self.assertEqual(suggest_mapping("totals_by_month", self.HEADERS, self.ROWS), {"date": "Order Date", "amount": "Total"})
        self.assertEqual(suggest_mapping("totals_by_group", self.HEADERS, self.ROWS)["amount"], "Total")

    def test_request_wording_picks_the_group(self):
        self.assertEqual(suggest_mapping("totals_by_group", self.HEADERS, self.ROWS, "total sales by item")["group"], "Item")
        self.assertEqual(suggest_mapping("totals_by_group", self.HEADERS, self.ROWS, "totals by region")["group"], "Region")

    def test_numbers_are_not_suggested_as_labels(self):
        mapping = suggest_mapping("revenue_by_product", ["Code", "Amount"], [["1", "2"], ["3", "4"]])
        self.assertNotIn("product", mapping)

    def test_optional_key_only_when_clearly_named(self):
        self.assertEqual(suggest_mapping("dedupe_rows", ["Name", "City"], [["a", "b"]]), {})
        self.assertEqual(suggest_mapping("dedupe_rows", ["Email", "Name"], [["a@b.c", "A"]]), {"key": "Email"})

    def test_validation(self):
        validate_columns("totals_by_month", self.HEADERS, self.ROWS, {"date": "Order Date", "amount": "Total"})
        with self.assertRaisesRegex(ValueError, "date column"):
            validate_columns("totals_by_month", self.HEADERS, self.ROWS, {"date": "Region", "amount": "Total"})
        with self.assertRaisesRegex(ValueError, "only be used once"):
            validate_columns("totals_by_group", self.HEADERS, self.ROWS, {"group": "Total", "amount": "Total"})
        with self.assertRaisesRegex(ValueError, "Choose the amount"):
            validate_columns("totals_by_group", self.HEADERS, self.ROWS, {"group": "Region"})
        self.assertEqual(validate_columns("dedupe_rows", self.HEADERS, self.ROWS, {"key": ""}), {})
        self.assertEqual(validate_columns("clean_table", self.HEADERS, self.ROWS, {}), {})


class DateToolTests(unittest.TestCase):
    def test_formats_and_column_order(self):
        self.assertEqual(parse_dates(["03/15/2026", "2026-01-02", "15 Mar 2026", "Mar 3, 2026", "2026/4/5"]),
                         ["2026-03-15", "2026-01-02", "2026-03-15", "2026-03-03", "2026-04-05"])
        self.assertEqual(parse_dates(["15/03/2026", "04/05/2026"]), ["2026-03-15", "2026-05-04"])

    def test_rejects_unreadable_ambiguous_and_impossible(self):
        for values in (["soon"], ["15/03/2026", "03/15/2026"], ["2026-02-30"]):
            with self.subTest(values=values):
                with self.assertRaises(ToolError):
                    parse_dates(values)

    def test_loose_columns(self):
        self.assertEqual(resolve_column(["Order Date", "Total"], "order_date"), "Order Date")
        with self.assertRaises(ToolError):
            resolve_column(["Total", "total"], "TOTAL ")


class ExcelTests(unittest.TestCase):
    def workbook(self, rows):
        book = Workbook()
        for row in rows:
            book.active.append(row)
        buffer = io.BytesIO()
        book.save(buffer)
        return buffer.getvalue()

    def test_converts_first_sheet_values(self):
        from datetime import date
        content = xlsx_to_csv(self.workbook([[None], ["Product", "Sales", "When"], ["Pen", 12.5, date(2026, 3, 1)],
                                             ["Ink", 3.0, None]]))
        headers, rows = parse_csv(content)
        self.assertEqual(headers, ["Product", "Sales", "When"])
        self.assertEqual(rows, [["Pen", "12.5", "2026-03-01"], ["Ink", "3", ""]])

    def test_rejects_non_xlsx_and_stray_values(self):
        with self.assertRaises(ValueError):
            xlsx_to_csv(b"not a zip")
        with self.assertRaisesRegex(ValueError, "outside the header"):
            xlsx_to_csv(self.workbook([["A", "B"], ["1", "2", "3"]]))


class NewRepairTests(unittest.TestCase):
    MONTH = {"date_column": "Date", "amount_column": "Amount"}
    EXPORTED = b'Date,Amount\n03/15/2026,"$1,000"\n"Mar 20, 2026",5\n04/01/2026,(2)\n'

    def test_strategy_names_are_unique(self):
        self.assertEqual(len({s.name for s in STRATEGIES}), len(STRATEGIES))

    def test_dates_then_amounts_stack_into_one_fix(self):
        skill = SKILLS["totals_by_month"]
        first = run_skill(skill.source, inputs=self.MONTH, files={"data_csv": self.EXPORTED}, tools=skill.contract["tools"])
        self.assertEqual(first.error["code"], "DATE_FORMAT")
        dates = NormalizeDates().patch(Failure("DATE_FORMAT", "x", {"value": "03/15/2026"}), skill.source, skill.contract)
        second = run_skill(dates.source, inputs=self.MONTH, files={"data_csv": self.EXPORTED}, tools=dates.contract["tools"])
        self.assertEqual(second.error["code"], "BAD_NUMBER")
        amounts = STRATEGIES[0].patch(Failure("BAD_NUMBER", "x", {}), dates.source, dates.contract)
        fixtures = skill.fixtures[:2] + dates.fixtures + amounts.fixtures + [
            failing_input_fixture("1.1.0", self.MONTH, {"data_csv": self.EXPORTED})]
        self.assertEqual(run_fixture_tests(amounts.source, amounts.contract, fixtures)["test_count"], 5)
        result = run_skill(amounts.source, inputs=self.MONTH, files={"data_csv": self.EXPORTED}, tools=amounts.contract["tools"])
        self.assertEqual(result.output["periods"], [{"period": "2026-03", "total": "1005", "row_count": 2},
                                                    {"period": "2026-04", "total": "-2", "row_count": 1}])

    def test_loose_column_repair(self):
        skill = SKILLS["totals_by_group"]
        inputs = {"group_column": "region", "amount_column": "AMOUNT"}
        files = {"data_csv": b"Region,Amount\nN,1\nN,2\n"}
        failed = run_skill(skill.source, inputs=inputs, files=files, tools=skill.contract["tools"])
        failure = Failure(failed.error["code"], failed.error["message"], failed.error["details"])
        strategy = MatchColumnsLoosely()
        self.assertTrue(strategy.applies(failure, skill.source, skill.contract))
        patch = strategy.patch(failure, skill.source, skill.contract)
        self.assertFalse(strategy.applies(failure, patch.source, patch.contract))
        evidence = run_fixture_tests(patch.source, patch.contract,
                                     skill.fixtures + [failing_input_fixture("1.1.0", inputs, files)])
        self.assertEqual(evidence["test_count"], 4)

    def test_loose_repair_refuses_ambiguous_headers(self):
        failure = Failure("MISSING_COLUMN", "x", {"column": "total", "available": ["Total", "TOTAL"]})
        self.assertFalse(MatchColumnsLoosely().applies(failure, SKILLS["totals_by_group"].source,
                                                       SKILLS["totals_by_group"].contract))


class StarterSkillTests(unittest.TestCase):
    def test_every_builtin_passes_its_fixtures(self):
        for skill in BUILTIN_SKILLS:
            with self.subTest(skill=skill.skill_id):
                self.assertTrue(run_fixture_tests(skill.source, skill.contract, skill.fixtures)["passed"])

    def test_file_skills_read_the_converted_file(self):
        self.assertTrue(all(f["name"] == "data_csv" for s in FILE_SKILLS for f in s.contract["inputs"] if f["type"] == "csv"))


if __name__ == "__main__":
    unittest.main()
