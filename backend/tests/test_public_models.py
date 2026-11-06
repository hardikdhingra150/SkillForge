import unittest
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from fastapi import HTTPException

from app.api.chat import check_site_budget
from app.llm import LLMError, ProviderStatus, get_provider, only
from app.llm.base import OWNER_ONLY, Provider
from app.security import LOCAL_WORKSPACE_ID, models_for, models_for_workspace


class Fake(Provider):
    id, label, kind = "claude", "Claude (fake)", "cli"

    def _status(self):
        return ProviderStatus(self.id, self.label, self.kind, True, "Logged in.", ["opus"], "opus")


class OwnerOnlyModelTests(unittest.TestCase):
    def test_visitors_see_owner_models_as_unavailable(self):
        provider = Fake()
        self.assertTrue(provider.status().available)
        with only(["ollama"]):
            hidden = provider.status()
        self.assertFalse(hidden.available)
        self.assertEqual(hidden.detail, OWNER_ONLY)
        self.assertEqual((hidden.models, hidden.default_model), ([], None))
        self.assertTrue(provider.status().available, "the limit ends with the block")

    def test_visitors_cannot_call_owner_models(self):
        with only(["ollama"]), self.assertRaises(LLMError):
            get_provider("claude")
        self.assertEqual(get_provider("claude").id, "claude")

    def test_who_gets_which_models(self):
        visitor = SimpleNamespace(state=SimpleNamespace(browser=True))
        owner = SimpleNamespace(state=SimpleNamespace())
        with mock.patch("app.security.settings.public_providers", ["ollama"]):
            self.assertEqual(models_for(visitor), ["ollama"])
            self.assertIsNone(models_for(owner))
            with mock.patch("app.security.settings.auth_mode", "browser"):
                self.assertEqual(models_for_workspace(uuid4()), ["ollama"])
                self.assertIsNone(models_for_workspace(LOCAL_WORKSPACE_ID))
            with mock.patch("app.security.settings.auth_mode", "off"):
                self.assertIsNone(models_for_workspace(uuid4()))

    def test_site_wide_chat_limit(self):
        check_site_budget(499, 500)
        with self.assertRaises(HTTPException) as caught:
            check_site_budget(500, 500)
        self.assertEqual(caught.exception.status_code, 429)


class ClaudeTokenTests(unittest.TestCase):
    def test_a_login_token_counts_as_logged_in_and_reaches_only_the_cli(self):
        from app.llm.base import minimal_env
        from app.llm.registry import ClaudeCLI

        with mock.patch.dict("os.environ", {"CLAUDE_CODE_OAUTH_TOKEN": "tok", "DATABASE_URL": "secret"}), \
                mock.patch("shutil.which", return_value="/usr/bin/claude"), mock.patch("subprocess.run") as run:
            status = ClaudeCLI()._status()
            env = minimal_env()
        self.assertTrue(status.available)
        run.assert_not_called()
        self.assertEqual(env.get("CLAUDE_CODE_OAUTH_TOKEN"), "tok")
        self.assertNotIn("DATABASE_URL", env)
