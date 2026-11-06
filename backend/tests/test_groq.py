import io
import json
import unittest
import urllib.error
from unittest import mock

from app.llm import LLMError
from app.llm.base import minimal_env
from app.llm.registry import Groq


def reply(body):
    response = mock.MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps(body).encode()
    return response


MODELS = {"data": [{"id": "whisper-large-v3"}, {"id": "llama-3.1-8b-instant"}, {"id": "llama-3.3-70b-versatile"},
                   {"id": "some-new-model"}]}


class GroqTests(unittest.TestCase):
    def test_without_a_key_it_says_how_to_connect(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            status = Groq()._status()
        self.assertFalse(status.available)
        self.assertIn("GROQ_API_KEY", status.detail)

    def test_lists_chat_models_with_the_preferred_one_first(self):
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}), \
                mock.patch("urllib.request.urlopen", return_value=reply(MODELS)):
            status = Groq()._status()
        self.assertTrue(status.available)
        self.assertEqual(status.models, ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "some-new-model"])
        self.assertEqual(status.default_model, "llama-3.3-70b-versatile")

    def test_a_refused_key(self):
        refused = urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b""))
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "gsk_bad"}), \
                mock.patch("urllib.request.urlopen", side_effect=refused):
            self.assertIn("refused", Groq()._status().detail)

    def test_complete_sends_the_conversation_and_returns_the_text(self):
        provider = Groq()
        answer = {"choices": [{"message": {"content": "Paris"}}]}
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}), \
                mock.patch("urllib.request.urlopen", side_effect=[reply(MODELS), reply(answer)]) as opened:
            text = provider.complete("Capital of France?", system="Be brief.")
        sent = json.loads(opened.call_args.args[0].data)
        self.assertEqual(text, "Paris")
        self.assertEqual(sent["model"], "llama-3.3-70b-versatile")
        self.assertEqual([m["role"] for m in sent["messages"]], ["system", "user"])
        self.assertEqual(opened.call_args.args[0].get_header("Authorization"), "Bearer gsk_test")

    def test_free_tier_limit_is_explained(self):
        provider = Groq()
        limited = urllib.error.HTTPError("u", 429, "slow down", {}, io.BytesIO(b"rate limit"))
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}), \
                mock.patch("urllib.request.urlopen", side_effect=[reply(MODELS), limited]), \
                self.assertRaises(LLMError) as caught:
            provider.complete("hi")
        self.assertIn("free-tier limit", str(caught.exception))

    def test_the_key_never_reaches_skills_or_command_line_tools(self):
        with mock.patch.dict("os.environ", {"GROQ_API_KEY": "gsk_test"}):
            self.assertNotIn("GROQ_API_KEY", minimal_env())
