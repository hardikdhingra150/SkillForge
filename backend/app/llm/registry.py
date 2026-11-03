import json
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from app.llm.base import LLMError, Provider, ProviderStatus, minimal_env, run_cli, scratch_dir

OLLAMA_URL = "http://127.0.0.1:11434"
PREFERRED_LOCAL_MODEL = "qwen2.5-coder:3b"


class ClaudeCLI(Provider):
    id, label, kind = "claude", "Claude (Claude Code CLI)", "cli"

    def _status(self):
        if shutil.which("claude") is None:
            return ProviderStatus(self.id, self.label, self.kind, False, "Install Claude Code to use Claude.")
        done = subprocess.run(["claude", "auth", "status"], capture_output=True, text=True, timeout=20, env=minimal_env())
        try:
            info = json.loads(done.stdout)
        except ValueError:
            return ProviderStatus(self.id, self.label, self.kind, False, "Could not read `claude auth status`.")
        if not info.get("loggedIn"):
            return ProviderStatus(self.id, self.label, self.kind, False,
                                  "Not logged in. Run `claude` in a terminal and use /login.")
        return ProviderStatus(self.id, self.label, self.kind, True, f"Logged in ({info.get('authMethod', 'account')}).",
                              ["default", "sonnet", "opus", "haiku"], "default")

    def complete(self, prompt, *, system=None, model=None, timeout=180):
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


class CodexCLI(Provider):
    id, label, kind = "codex", "Codex (OpenAI Codex CLI)", "cli"

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


PROVIDERS: dict[str, Provider] = {p.id: p for p in (ClaudeCLI(), CodexCLI(), Ollama())}


def get_provider(provider_id: str) -> Provider:
    if provider_id not in PROVIDERS:
        raise LLMError(f"Unknown provider {provider_id!r}.")
    return PROVIDERS[provider_id]


def provider_statuses(refresh: bool = False) -> list[ProviderStatus]:
    return [provider.status(refresh) for provider in PROVIDERS.values()]
