import unittest
from unittest.mock import patch

from app.llm.base import LLMError
from app.llm.registry import Ollama


class OllamaPrivacyTests(unittest.TestCase):
    def test_rejects_models_outside_local_inventory_before_sending_prompt(self):
        provider = Ollama()
        with patch.object(provider, "_get", return_value={"models": [
            {"name": "local:latest"},
            {"name": "remote:latest", "remote_host": "https://example.invalid"},
        ]}), patch("app.llm.registry.urllib.request.urlopen") as urlopen:
            with self.assertRaisesRegex(LLMError, "installed local Ollama model"):
                provider.complete("private input", model="remote:latest")
            urlopen.assert_not_called()
