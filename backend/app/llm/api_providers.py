"""API-key providers for deployed SkillForge: the Anthropic API and the OpenAI API.

Keys come only from the server environment (ANTHROPIC_API_KEY, OPENAI_API_KEY);
they are never stored in the database or sent to the browser.
"""

import anthropic
import openai

from app.config import settings
from app.llm.base import LLMError, Provider, ProviderStatus


def _secret(value):
    return value.get_secret_value() if value else None

ANTHROPIC_MODELS = ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"]


class AnthropicAPI(Provider):
    id, label, kind = "anthropic", "Claude API (Anthropic)", "api"
    setup = [
        {"label": "Create an API key at platform.claude.com, then add it to backend/.env",
         "command": "echo 'ANTHROPIC_API_KEY=sk-ant-...' >> backend/.env"},
        {"label": "Restart the API", "command": "make api"},
    ]

    def _status(self):
        if not _secret(settings.anthropic_api_key):
            return ProviderStatus(self.id, self.label, self.kind, False, "Set ANTHROPIC_API_KEY in backend/.env.")
        return ProviderStatus(self.id, self.label, self.kind, True, "API key configured.", ANTHROPIC_MODELS, ANTHROPIC_MODELS[0])

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        key = _secret(settings.anthropic_api_key)
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set.")
        client = anthropic.Anthropic(api_key=key, timeout=timeout, max_retries=2)
        try:
            # Refusal fallbacks are on by default: a declined request is re-run on a fallback model.
            response = client.beta.messages.create(
                model=model or ANTHROPIC_MODELS[0],
                max_tokens=16000,
                system=system or anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
                output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError:
            raise LLMError("The Anthropic API key was rejected.") from None
        except anthropic.RateLimitError:
            raise LLMError("The Anthropic API is rate limiting requests; try again shortly.") from None
        except anthropic.APIStatusError as error:
            raise LLMError(f"Anthropic API error {error.status_code}: {error.message}") from None
        except anthropic.APIConnectionError:
            raise LLMError("Could not reach the Anthropic API.") from None
        if response.stop_reason == "refusal":
            raise LLMError("Claude declined this request.")
        return "".join(block.text for block in response.content if block.type == "text")


class OpenAIAPI(Provider):
    id, label, kind = "openai", "OpenAI API", "api"
    setup = [
        {"label": "Create an API key at platform.openai.com, then add it to backend/.env",
         "command": "echo 'OPENAI_API_KEY=sk-...' >> backend/.env"},
        {"label": "Optional: choose the model (default gpt-5)", "command": "echo 'OPENAI_MODEL=gpt-5' >> backend/.env"},
        {"label": "Restart the API", "command": "make api"},
    ]

    def _status(self):
        if not _secret(settings.openai_api_key):
            return ProviderStatus(self.id, self.label, self.kind, False, "Set OPENAI_API_KEY in backend/.env.")
        default = settings.openai_model
        return ProviderStatus(self.id, self.label, self.kind, True, "API key configured.", [default], default)

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        key = _secret(settings.openai_api_key)
        if not key:
            raise LLMError("OPENAI_API_KEY is not set.")
        client = openai.OpenAI(api_key=key, timeout=timeout, max_retries=2)
        try:
            response = client.responses.create(
                model=model or settings.openai_model,
                instructions=system or openai.NOT_GIVEN,
                input=prompt,
            )
        except openai.AuthenticationError:
            raise LLMError("The OpenAI API key was rejected.") from None
        except openai.RateLimitError:
            raise LLMError("The OpenAI API is rate limiting requests; try again shortly.") from None
        except openai.APIStatusError as error:
            raise LLMError(f"OpenAI API error {error.status_code}: {error.message}") from None
        except openai.APIConnectionError:
            raise LLMError("Could not reach the OpenAI API.") from None
        return response.output_text or ""
