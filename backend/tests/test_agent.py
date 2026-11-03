import json
import unittest
from unittest.mock import patch

from app.llm.base import Provider, complete_json, extract_json
from app.sandbox import PolicyViolation
from app.services.agent import build_candidate, needs_files, plan, prove, prove_with_arbitration
from app.services.skill_registry import ExampleMismatch

GOOD_SPEC = {
    "summary": "Count words in a text.",
    "inputs": [{"name": "text", "type": "text"}],
    "outputs": [{"name": "words", "type": "integer"}],
    "tools": [],
    "source": "def run(inputs, tools):\n    return {\"words\": len(inputs[\"text\"].split())}\n",
    "examples": [
        {"name": "two", "inputs": {"text": "hello world"}, "output": {"words": 2}},
        {"name": "empty", "inputs": {"text": ""}, "output": {"words": 0}},
        {"name": "spaces", "inputs": {"text": "  a   b c "}, "output": {"words": 3}},
    ],
}


class FakeProvider(Provider):
    id, label = "fake", "Fake"

    def __init__(self, replies):
        self.replies, self.prompts = list(replies), []

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        self.prompts.append(prompt)
        return self.replies.pop(0)


class JsonTests(unittest.TestCase):
    def test_extracts_json_from_fences_and_chatter(self):
        self.assertEqual(extract_json('Sure!\n```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(extract_json('prefix {"b": {"c": 2}} suffix'), {"b": {"c": 2}})
        with self.assertRaises(ValueError):
            extract_json("no json here")

    def test_complete_json_retries_once(self):
        provider = FakeProvider(["sorry", '{"ok": true}'])
        self.assertEqual(complete_json(provider, "q", system="s"), {"ok": True})
        self.assertIn("not a valid JSON object", provider.prompts[1])


class PlannerTests(unittest.TestCase):
    def test_skill_capability_is_normalized(self):
        provider = FakeProvider([json.dumps({"mode": "skill", "capability": "Count Words!", "inputs": {"text": "a b"}})])
        self.assertEqual(plan(provider, None, "", "", "count words")["capability"], "count_words")

    def test_skill_without_input_values_is_an_answer(self):
        # The 3B model routed "give me code to print hello world" to a skill with no inputs.
        provider = FakeProvider([json.dumps({"mode": "skill", "capability": "print_hello_world", "inputs": {}})])
        self.assertEqual(plan(provider, None, "", "", "give me code to print hello world")["mode"], "answer")

    def test_malformed_skill_plan_falls_back_to_answer(self):
        provider = FakeProvider([json.dumps({"mode": "skill", "capability": "x", "inputs": "nope"})])
        self.assertEqual(plan(provider, None, "", "", "?")["mode"], "answer")


class SmithProofTests(unittest.TestCase):
    def test_good_candidate_is_proven(self):
        source, contract, examples = build_candidate("count_words", GOOD_SPEC)
        evidence, output = prove(source, contract, examples, {"text": "one two three four"})
        self.assertEqual(evidence["test_count"], 3)
        self.assertEqual(output, {"words": 4})
        self.assertEqual(contract["checks"], ["contract_outputs"])

    def test_wrong_example_is_rejected(self):
        spec = {**GOOD_SPEC, "examples": [*GOOD_SPEC["examples"][:2], {"name": "bad", "inputs": {"text": "a"}, "output": {"words": 5}}]}
        source, contract, examples = build_candidate("count_words", spec)
        with self.assertRaises(ValueError):
            prove(source, contract, examples, {"text": "x"})

    def test_unsafe_source_and_too_few_examples_are_rejected(self):
        with self.assertRaises(PolicyViolation):
            build_candidate("count_words", {**GOOD_SPEC, "source": "import os\n" + GOOD_SPEC["source"]})
        with self.assertRaises(ValueError):
            build_candidate("count_words", {**GOOD_SPEC, "examples": GOOD_SPEC["examples"][:2]})

    def test_file_tools_are_not_granted_to_chat_skills(self):
        _, contract, _ = build_candidate("count_words", {**GOOD_SPEC, "tools": ["read_csv", "regex_findall"]})
        self.assertEqual(contract["tools"], ["regex_findall"])

    def test_verifier_disagreement_rejects_the_skill(self):
        source, contract, examples = build_candidate("count_words", GOOD_SPEC)
        with self.assertRaises(ValueError) as caught:
            prove(source, contract, examples, {"text": "a b"}, verifier=lambda inputs, output: (False, "expected 3"))
        self.assertIn("verifier", str(caught.exception))

    def test_csv_skills_are_kept_out_of_chat(self):
        self.assertTrue(needs_files({"inputs": [{"name": "sales_csv", "type": "csv"}]}))
        self.assertFalse(needs_files({"inputs": [{"name": "text", "type": "text"}]}))


class JudgeChoiceTests(unittest.TestCase):
    def available(self, *ids):
        statuses = {pid: type("S", (), {"available": pid in ids, "default_model": None})() for pid in ("codex", "claude", "ollama")}
        return patch.multiple("app.llm.registry.Provider", status=lambda self, refresh=False: statuses[self.id])

    def test_local_author_is_judged_by_a_stronger_model(self):
        from app.services.agent import pick_judge
        with self.available("codex", "ollama"):
            self.assertEqual(pick_judge("ollama", None)[0].id, "codex")

    def test_local_model_never_judges_codex(self):
        from app.services.agent import pick_judge
        with self.available("codex", "ollama"):
            self.assertEqual(pick_judge("codex", None)[0].id, "codex")
        with self.available("codex", "claude", "ollama"):
            self.assertEqual(pick_judge("codex", None)[0].id, "claude")


class ArbitrationTests(unittest.TestCase):
    """A wrong worked example (the 3B model miscounting) must not sink correct code, and vice versa."""

    def setUp(self):
        wrong = [*GOOD_SPEC["examples"][:2], {"name": "miscount", "inputs": {"text": "a b c d e f g"}, "output": {"words": 10}}]
        self.source, self.contract, self.examples = build_candidate("count_words", {**GOOD_SPEC, "examples": wrong})

    @patch("app.services.agent.add_step")
    def test_verifier_siding_with_code_corrects_the_example(self, _steps):
        judge = lambda request, capability, inputs, output: (True, "7 words")  # noqa: E731
        evidence, output, examples = prove_with_arbitration("m", judge, "Count words", "count_words", self.source,
                                                            self.contract, self.examples, {"text": "x y"}, lambda i, o: (True, ""))
        self.assertEqual(output, {"words": 2})
        fixed = next(e for e in examples if e[0] == "miscount")[3]
        self.assertEqual(fixed, {"output": {"words": 7}, "corrected_by_verifier": True})

    @patch("app.services.agent.add_step")
    def test_verifier_siding_with_example_rejects(self, _steps):
        judge = lambda request, capability, inputs, output: (False, "it is 10")  # noqa: E731
        with self.assertRaises(ExampleMismatch):
            prove_with_arbitration("m", judge, "Count words", "count_words", self.source, self.contract,
                                   self.examples, {"text": "x y"}, lambda i, o: (True, ""))


if __name__ == "__main__":
    unittest.main()
