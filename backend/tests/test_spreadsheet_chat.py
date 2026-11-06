import unittest
from unittest import mock

from app.services import agent

SALES = b"Product,Sales\nBackpack,\"$1,200.50\"\nPen,$40.00\n"


class SpreadsheetChatTests(unittest.TestCase):
    def test_requests_that_name_one_file_task(self):
        self.assertEqual(agent.spreadsheet_workflow("Total sales by region"), "totals_by_group")
        self.assertEqual(agent.spreadsheet_workflow("Show revenue by product"), "revenue_by_product")
        self.assertIsNone(agent.spreadsheet_workflow("Write a poem about the sea"))

    def test_runs_the_file_skill_with_suggested_columns_and_no_model(self):
        with mock.patch.object(agent, "add_step") as steps, \
                mock.patch.object(agent, "latest_validated", return_value=mock.Mock(skill_id="revenue_by_product",
                                                                                     version="1.0.0")), \
                mock.patch.object(agent, "SessionLocal"), \
                mock.patch.object(agent, "spreadsheet_author", return_value=(None, None, None)), \
                mock.patch.object(agent, "reuse_or_repair", return_value={"text": "ok", "skill": {}}) as run:
            agent.run_spreadsheet_task("m1", "revenue_by_product", {"sales.csv": {"content": SALES}},
                                       "Show revenue by product", "auto", None)
        args, kwargs = run.call_args
        self.assertEqual(args[4], ("revenue_by_product", "1.0.0"))
        self.assertEqual(args[5], {"product_column": "Product", "revenue_column": "Sales"})
        self.assertEqual(args[9], {"sales_csv": SALES})
        self.assertFalse(kwargs["model_check"])
        self.assertIn("No model is needed", steps.call_args_list[0].args[2])

    def test_asks_which_column_when_it_cannot_tell(self):
        rows = b"A,B\nx,y\nz,w\n"
        with mock.patch.object(agent, "add_step"), self.assertRaises(agent.NeedsInput) as asked:
            agent.run_spreadsheet_task("m1", "totals_by_group", {"f.csv": {"content": rows}}, "Total sales by region",
                                       "auto", None)
        self.assertIn("f.csv has: A, B", str(asked.exception))
