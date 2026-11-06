import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from app.llm.base import BRIDGE, OWNER_ONLY, LLMError, Provider, ProviderStatus, allowed, minimal_env, run_cli, scratch_dir

# In Docker the compose file points this at the host (host.docker.internal).
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
PREFERRED_LOCAL_MODEL = "qwen2.5-coder:3b"


CLAUDE_SETUP = [
    {"label": "Install Claude Code", "command": "curl -fsSL https://claude.ai/install.sh | bash"},
    {"label": "Log in (opens your browser)", "command": "claude auth login"},
    {"label": "Check", "command": "claude auth status"},
]
CODEX_SETUP = [
    {"label": "Install the Codex CLI", "command": "npm install -g @openai/codex"},
    {"label": "Log in with ChatGPT (opens your browser)", "command": "codex login"},
    {"label": "Check", "command": "codex login status"},
]
OLLAMA_SETUP = [
    {"label": "Install Ollama", "command": "brew install ollama"},
    {"label": "Start it", "command": "ollama serve"},
    {"label": "Download the local model (about 1.9 GB)", "command": "ollama pull qwen2.5-coder:3b"},
]


class BridgeableCLI(Provider):
    """A CLI that, for a visitor, runs on the visitor's own computer instead (services/bridge.py)."""

    server_label = ""
    bridged_label = ""

    @property
    def label(self):
        return self.bridged_label if BRIDGE.get() is not None else self.server_label


class ClaudeCLI(BridgeableCLI):
    id, kind = "claude", "cli"
    server_label, bridged_label = "Claude (Claude Code CLI)", "Claude (your computer)"
    setup = CLAUDE_SETUP

    def _status(self):
        if shutil.which("claude") is None:
            return ProviderStatus(self.id, self.label, self.kind, False, "Install Claude Code to use Claude.")
        if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):  # a long-lived login from `claude setup-token`
            return ProviderStatus(self.id, self.label, self.kind, True, "Logged in with a token.",
                                  ["default", "sonnet", "opus", "haiku"], "default")
        done = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True, timeout=20, env=minimal_env())
        try:
            info = json.loads(done.stdout)
        except ValueError:
            return ProviderStatus(self.id, self.label, self.kind, False, "Could not read `claude auth status`.")
        if not info.get("loggedIn"):
            return ProviderStatus(self.id, self.label, self.kind, False,
                                  "Not logged in. Run `claude auth login` in a terminal.")
        return ProviderStatus(self.id, self.label, self.kind, True, f"Logged in ({info.get('authMethod', 'account')}).",
                              ["default", "sonnet", "opus", "haiku"], "default")

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        if (bridge := BRIDGE.get()) is not None:
            return bridge.complete(self.id, prompt, system=system, model=model, timeout=timeout)
        args = ["claude", "-p", "--output-format", "json", "--tools", "", "--no-session-persistence",
                "--strict-mcp-config", "--disable-slash-commands"]
        if system:
            args += ["--system-prompt", system]
        if model and model != "default":
            args += ["--model", model]
        with scratch_dir() as cwd:
            done = run_cli(args, stdin=prompt, timeout=timeout, cwd=cwd)
        try:
            reply = json.loads(done.stdout)
        except ValueError:
            raise LLMError((done.stderr or done.stdout or "Claude returned no output.").strip()[:400]) from None
        if reply.get("is_error"):
            raise LLMError(f"Claude: {reply.get('result') or reply.get('terminal_reason')}")
        return reply.get("result", "")


class CodexCLI(BridgeableCLI):
    id, kind = "codex", "cli"
    server_label, bridged_label = "Codex (OpenAI Codex CLI)", "Codex (your computer)"
    setup = CODEX_SETUP

    def _status(self):
        if shutil.which("codex") is None:
            return ProviderStatus(self.id, self.label, self.kind, False, "Install the Codex CLI to use Codex.")
        done = subprocess.run(["codex", "login", "status"], capture_output=True, text=True, timeout=20, env=minimal_env())
        text = (done.stdout + done.stderr).strip()
        if done.returncode != 0 or "not logged in" in text.lower():
            return ProviderStatus(self.id, self.label, self.kind, False, "Not logged in. Run `codex login` in a terminal.")
        return ProviderStatus(self.id, self.label, self.kind, True, text.splitlines()[0] if text else "Logged in.",
                              ["default"], "default")

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        if (bridge := BRIDGE.get()) is not None:
            return bridge.complete(self.id, prompt, system=system, model=model, timeout=timeout)
        full = f"{system}\n\n---\n\n{prompt}" if system else prompt
        with scratch_dir() as cwd:
            out = Path(cwd) / "reply.txt"
            args = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                    "-C", cwd, "-o", str(out), "--color", "never"]
            if model and model != "default":
                args += ["-m", model]
            done = run_cli([*args, "-"], stdin=full, timeout=timeout, cwd=cwd)
            reply = out.read_text().strip() if out.exists() else ""
        if done.returncode != 0 or not reply:
            raise LLMError(f"Codex: {(done.stderr or done.stdout or 'no reply').strip().splitlines()[-1][:400]}")
        return reply


class Ollama(Provider):
    id, label, kind = "ollama", "Local model (Ollama)", "local"
    setup = OLLAMA_SETUP

    def _get(self, path, timeout=5):
        with urllib.request.urlopen(OLLAMA_URL + path, timeout=timeout) as response:
            return json.loads(response.read())

    def _status(self):
        try:
            tags = self._get("/api/tags")
        except (urllib.error.URLError, OSError):
            return ProviderStatus(self.id, self.label, self.kind, False, "Ollama is not running. Start it with `ollama serve`.")
        local = [m["name"] for m in tags.get("models", []) if not m["name"].endswith(":cloud") and not m.get("remote_host")]
        if not local:
            return ProviderStatus(self.id, self.label, self.kind, False,
                                  f"No local model yet. Run `ollama pull {PREFERRED_LOCAL_MODEL}`.")
        default = PREFERRED_LOCAL_MODEL if PREFERRED_LOCAL_MODEL in local else local[0]
        return ProviderStatus(self.id, self.label, self.kind, True, f"{len(local)} local model(s) on this machine.",
                              local, default)

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        status = self.status()
        if not status.available:
            raise LLMError(status.detail)
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        body = json.dumps({"model": model or status.default_model, "messages": messages, "stream": False,
                           "options": {"temperature": 0.2}}).encode()
        request = urllib.request.Request(OLLAMA_URL + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                reply = json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise LLMError(f"Ollama: {error.read().decode(errors='replace')[:300]}") from None
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            raise LLMError(f"Ollama did not answer: {error}") from None
        if reply.get("error"):
            raise LLMError(f"Ollama: {reply['error']}")
        return reply.get("message", {}).get("content", "")


GROQ_URL = "https://api.groq.com/openai/v1"
# Tried in order; the first one this key can use becomes the default. Groq retires models, so the list of what is
# actually offered comes from its /models endpoint, not from here.
GROQ_PREFERRED = ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant")
GROQ_SETUP = [
    {"label": "Create a free API key (no card needed)", "command": "https://console.groq.com/keys"},
    {"label": "Give it to the server as GROQ_API_KEY, then restart it", "command": "GROQ_API_KEY=gsk_..."},
]


class Groq(Provider):
    """Groq's hosted models through its OpenAI-compatible API (free tier, no card). Needs GROQ_API_KEY."""

    id, label, kind = "groq", "Groq (hosted, free tier)", "api"
    setup = GROQ_SETUP

    def _key(self):
        return os.environ.get("GROQ_API_KEY", "").strip()

    def _call(self, path, body=None, timeout=10):
        request = urllib.request.Request(GROQ_URL + path, data=json.dumps(body).encode() if body is not None else None,
                                         headers={"Authorization": f"Bearer {self._key()}",
                                                  "Content-Type": "application/json",
                                                  "User-Agent": "SkillForge"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())

    def _status(self):
        if not self._key():
            return ProviderStatus(self.id, self.label, self.kind, False, "Set GROQ_API_KEY to use Groq.")
        try:
            listed = [m["id"] for m in self._call("/models").get("data", []) if m.get("active", True)]
        except urllib.error.HTTPError as error:
            detail = "The GROQ_API_KEY was refused." if error.code in (401, 403) else f"Groq answered {error.code}."
            return ProviderStatus(self.id, self.label, self.kind, False, detail)
        except (urllib.error.URLError, OSError, ValueError):
            return ProviderStatus(self.id, self.label, self.kind, False, "Groq can't be reached right now.")
        chat = [m for m in listed if not any(word in m for word in ("whisper", "tts", "guard", "embed"))]
        preferred = [m for m in GROQ_PREFERRED if m in chat]
        models = preferred + sorted(m for m in chat if m not in preferred)
        if not models:
            return ProviderStatus(self.id, self.label, self.kind, False, "This Groq key has no chat models.")
        return ProviderStatus(self.id, self.label, self.kind, True, f"Connected ({len(models)} models).",
                              models, models[0])

    def complete(self, prompt, *, system=None, model=None, timeout=180):
        status = self.status()
        if not status.available:
            raise LLMError(status.detail)
        messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        try:
            reply = self._call("/chat/completions", {"model": model or status.default_model, "messages": messages,
                                                     "temperature": 0.2}, timeout=timeout)
        except urllib.error.HTTPError as error:
            body = error.read().decode(errors="replace")[:300]
            if error.code == 429:
                raise LLMError("Groq's free-tier limit was reached. Try again in a minute.") from None
            raise LLMError(f"Groq: {body}") from None
        except (urllib.error.URLError, OSError, TimeoutError) as error:
            raise LLMError(f"Groq did not answer: {error}") from None
        try:
            return reply["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError):
            raise LLMError("Groq returned an unexpected reply.") from None


PROVIDERS: dict[str, Provider] = {p.id: p for p in (ClaudeCLI(), CodexCLI(), Groq(), Ollama())}


def get_provider(provider_id: str) -> Provider:
    if provider_id not in PROVIDERS:
        raise LLMError(f"Unknown provider {provider_id!r}.")
    if not allowed(provider_id):
        raise LLMError(f"{PROVIDERS[provider_id].label}: {OWNER_ONLY}")
    return PROVIDERS[provider_id]


def provider_statuses(refresh: bool = False) -> list[ProviderStatus]:
    return [provider.status(refresh) for provider in PROVIDERS.values()]
