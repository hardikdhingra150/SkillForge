import json
import unittest

from app.llm.base import Provider
from app.schemas.skill_contract import SkillContract
from app.services.agent import NeedsInput, bind_chat_inputs, plan
from app.services.discovery import discover, remap_inputs, tokens
from app.services.request_queue import review_requested
from app.services.requirement_review import review_with_model
from app.skills import STARTER_SKILLS

SKILLS = {
    "extract_emails": {"summary": "Extract email addresses.", "inputs": ["text"]},
    "count_words": {"summary": "Count words.", "inputs": ["text"]},
    "convert_temperature": {"summary": "Convert temperatures.", "inputs": ["value", "from_unit", "to_unit"]},
    "dedupe_list": {"summary": "Remove duplicates.", "inputs": ["items", "case_sensitive"]},
}


class FakeProvider(Provider):
    id, label = "fake", "Fake"

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        self.prompts.append(prompt)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class DiscoveryTests(unittest.TestCase):
    def test_synonyms_reuse_without_a_model(self):
        for planned in ("pull_emails", "get_email_addresses", "extract_email_list"):
            with self.subTest(planned=planned):
                match = discover(planned, {"text": "x"}, SKILLS)
                self.assertEqual((match.capability, match.how), ("extract_emails", "names"))
        self.assertEqual(discover("remove_duplicates", {"items": [1]}, SKILLS).capability, "dedupe_list")

    def test_exact_and_unrelated(self):
        self.assertEqual(discover("count_words", {"text": "a"}, SKILLS).how, "exact")
        self.assertEqual(discover("translate_to_french", {"text": "a"}, SKILLS).how, "new")

    def test_close_calls_ask_the_model_and_respect_a_no(self):
        no = FakeProvider([json.dumps({"same": False, "reason": "sentences are not words"})] * 3)
        match = discover("count_sentences", {"text": "a. b."}, SKILLS, provider=no, request="count the sentences")
        self.assertEqual(match.how, "new")
        self.assertIn("count_words", no.prompts[0])

    def test_model_yes_maps_inputs_to_the_skill(self):
        yes = FakeProvider([json.dumps({"same": True, "input_mapping": {"celsius": "value"}, "reason": "unit conversion"})])
        match = discover("celsius_to_kelvin", {"celsius": 25}, SKILLS, provider=yes)
        self.assertEqual((match.capability, match.how), ("convert_temperature", "model"))
        self.assertEqual(match.inputs, {"value": 25})

    def test_without_a_strong_model_close_calls_create_new(self):
        self.assertEqual(discover("celsius_to_kelvin", {"value": 25}, SKILLS).how, "new")

    def test_remapping_and_tokens(self):
        self.assertEqual(remap_inputs({"content": "x"}, ["text"]), {"text": "x"})
        self.assertEqual(remap_inputs({"text": "x", "n": 1}, ["text", "limit"]), {"text": "x", "limit": 1})
        self.assertEqual(tokens("total_sales_per_item"), frozenset({"total", "revenue", "product"}))


class ClarifyTests(unittest.TestCase):
    def test_planner_can_ask_a_question(self):
        reply = json.dumps({"mode": "clarify", "question": "Which temperature should I convert?"})
        self.assertEqual(plan(FakeProvider([reply]), None, "", "", "convert this temperature"),
                         {"mode": "clarify", "question": "Which temperature should I convert?"})

    def test_clarify_without_a_question_is_an_answer(self):
        self.assertEqual(plan(FakeProvider([json.dumps({"mode": "clarify"})]), None, "", "", "hm")["mode"], "answer")

    def test_missing_input_becomes_a_question(self):
        contract = SkillContract.model_validate(next(s for s in STARTER_SKILLS if s.skill_id == "convert_temperature").contract)
        with self.assertRaises(NeedsInput) as caught:
            bind_chat_inputs(contract, {"value": 100})
        self.assertIn("What should I use?", str(caught.exception))


class ContractAwareVerifierTests(unittest.TestCase):
    def test_verifier_sees_the_documented_defaults(self):
        from app.services.agent import verify_output
        dedupe = next(s for s in STARTER_SKILLS if s.skill_id == "dedupe_list")
        provider = FakeProvider([json.dumps({"correct": True, "reason": "case-insensitive by default"})])
        correct, _ = verify_output(provider, None, "remove duplicates: apple, Apple", "dedupe_list",
                                   {"items": ["apple", "Apple"]}, {"items": ["apple"], "removed": 1}, dedupe.contract)
        self.assertTrue(correct)
        self.assertIn("case-insensitively", provider.prompts[0])
        self.assertIn("case_sensitive (boolean, optional)", provider.prompts[0])


class WorkbenchReviewTests(unittest.TestCase):
    CLAIM = {"requirement": "how much did each item sell for in total", "clarifications": []}

    def test_confident_model_accepts_varied_wording(self):
        provider = FakeProvider([json.dumps({"workflow": "revenue_by_product", "confidence": 0.9, "summary": "Revenue per item."})])
        review = review_requested(self.CLAIM, provider)
        self.assertEqual((review.method, review.candidate_workflow, review.next_action),
                         ("llm_review_v1", "revenue_by_product", "upload_csv"))

    def test_unsure_model_asks_one_question(self):
        provider = FakeProvider([json.dumps({"workflow": "revenue_by_product", "confidence": 0.4,
                                             "question": "Revenue per product, or units sold per product?"})])
        review = review_with_model("sales by product", [], provider)
        self.assertEqual(review.next_action, "clarify_requirement")
        self.assertEqual(review.input_message, "Revenue per product, or units sold per product?")

    def test_keyword_match_skips_the_model(self):
        provider = FakeProvider([])
        review = review_requested({"requirement": "Show revenue by product", "clarifications": []}, provider)
        self.assertEqual((review.method, review.candidate_workflow), ("keyword_rules_v1", "revenue_by_product"))
        self.assertEqual(provider.prompts, [])

    def test_clarification_answer_counts_for_the_keyword_rules(self):
        review = review_requested({"requirement": "analyze my file", "clarifications": ["revenue by product please"]}, None)
        self.assertEqual(review.candidate_workflow, "revenue_by_product")

    def test_model_failure_falls_back_to_rules(self):
        review = review_requested(self.CLAIM, FakeProvider([RuntimeError("model down")]))
        self.assertEqual(review.method, "keyword_rules_v1")


if __name__ == "__main__":
    unittest.main()
