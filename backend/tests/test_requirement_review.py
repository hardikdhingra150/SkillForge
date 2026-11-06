import json
import unittest

from app.services.requirement_review import (
    review_requirement,
)


class RequirementReviewTests(
    unittest.TestCase
):
    def test_sample_request_proposes_csv_workflow(
        self,
    ):
        review = review_requirement(
            "Show revenue by product "
            "from my sales data."
        )

        self.assertEqual(
            review.candidate_workflow,
            "revenue_by_product",
        )

        self.assertEqual(
            review.next_action,
            "upload_csv",
        )

        self.assertTrue(
            review.requires_confirmation
        )

    def test_case_and_whitespace(self):
        review = review_requirement(
            "  SHOW REVENUE  GROUPED\n"
            "BY PRODUCTS "
        )

        self.assertEqual(
            review.next_action,
            "upload_csv",
        )

    def test_unrelated_request_needs_clarification(
        self,
    ):
        review = review_requirement(
            "Create a presentation "
            "about climate change."
        )

        self.assertIsNone(
            review.candidate_workflow
        )

        self.assertEqual(
            review.next_action,
            "clarify_requirement",
        )

    def test_negation_needs_clarification(
        self,
    ):
        examples = [
            "Do not show revenue by product.",
            "Don't calculate revenue by product.",
            "Don’t calculate revenue by product.",
        ]

        for requirement in examples:
            with self.subTest(
                requirement=requirement
            ):
                review = review_requirement(
                    requirement
                )

                self.assertIsNone(
                    review.candidate_workflow
                )

    def test_forecasting_needs_clarification(
        self,
    ):
        review = review_requirement(
            "Forecast revenue by product."
        )

        self.assertEqual(
            review.next_action,
            "clarify_requirement",
        )

    def test_extra_grouping_needs_clarification(
        self,
    ):
        review = review_requirement(
            "Show revenue by product "
            "and region."
        )

        self.assertEqual(
            review.next_action,
            "clarify_requirement",
        )

    def test_word_boundaries(self):
        review = review_requirement(
            "Show revenue by production line."
        )

        self.assertIsNone(
            review.candidate_workflow
        )

    def test_payload_is_json_serializable(
        self,
    ):
        payload = review_requirement(
            "Show revenue by product."
        ).payload()

        self.assertEqual(
            payload["required_inputs"],
            ["sales_csv"],
        )

        self.assertEqual(
            payload["method"],
            "keyword_rules_v1",
        )

        self.assertTrue(
            payload["requires_confirmation"]
        )

        json.dumps(payload)


if __name__ == "__main__":
    unittest.main()

class ChatRequestTests(unittest.TestCase):
    def test_requests_that_are_not_about_a_table_are_sent_to_chat(self):
        for text in ("make a new skill to make every text humanised", "Write a poem about the sea",
                     "convert 5 miles to kilometres"):
            with self.subTest(text=text):
                review = review_requirement(text)
                self.assertTrue(review.suggest_chat)
                self.assertIn("Chat", review.input_message)
                self.assertIsNone(review.candidate_workflow)

    def test_unclear_spreadsheet_requests_still_get_a_question(self):
        review = review_requirement("Analyze my data file")
        self.assertFalse(review.suggest_chat)
        self.assertEqual(review.next_action, "clarify_requirement")

    def test_the_model_can_send_a_request_to_chat(self):
        from unittest import mock

        from app.services import requirement_review
        with mock.patch("app.llm.complete_json", return_value={"workflow": None, "confidence": 0.1, "chat": True}):
            review = requirement_review.review_with_model("summarise this article", [], provider=object())
        self.assertTrue(review.suggest_chat)
        self.assertEqual(review.method, "llm_review_v1")
