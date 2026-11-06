import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field, replace

# Only what a CLI needs to find its own login; never app settings or database secrets.
# CLAUDE_CODE_OAUTH_TOKEN is the owner's own login on hosts without a disk (from `claude setup-token`); it goes
# only to the Claude CLI's process, never to skills, which run with no environment at all.
PASSTHROUGH_ENV = ("HOME", "PATH", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM",
                   "CLAUDE_CONFIG_DIR", "CODEX_HOME", "CLAUDE_CODE_OAUTH_TOKEN")
STATUS_TTL = 30.0

# The providers the current request may use (None: all). On a public site, visitors get only the free local
# model; the CLIs run on the owner's personal logins, so only the owner (API_TOKEN) may use them.
ALLOWED: ContextVar[frozenset | None] = ContextVar("allowed_providers", default=None)
OWNER_ONLY = "Only the site owner can use this model here."


@contextmanager
def only(providers):
    """Limit every provider lookup in this block (and the threads it runs inline) to `providers`."""
    token = ALLOWED.set(None if providers is None else frozenset(providers))
    try:
        yield
    finally:
        ALLOWED.reset(token)


def allowed(provider_id: str) -> bool:
    limit = ALLOWED.get()
    return limit is None or provider_id in limit


class LLMError(RuntimeError):
    """The provider could not produce an answer (not installed, not logged in, timed out, refused)."""


@dataclass(frozen=True)
class ProviderStatus:
    id: str
    label: str
    kind: str  # "cli" or "local"
    available: bool
    detail: str
    models: list[str] = field(default_factory=list)
    default_model: str | None = None
    # Exact terminal commands to install and connect this provider: [{"label", "command"}].
    setup: list[dict] = field(default_factory=list)

    def payload(self):
        return asdict(self)


class Provider:
    id = ""
    label = ""
    kind = "cli"
    _cached: tuple[float, ProviderStatus] | None = None

    setup: list[dict] = []

    def status(self, refresh: bool = False) -> ProviderStatus:
        if not refresh and self._cached and time.monotonic() - self._cached[0] < STATUS_TTL:
            return self._visible(self._cached[1])
        try:
            status = self._status()
        except Exception as error:  # status must never take the API down
            status = ProviderStatus(self.id, self.label, self.kind, False, f"Status check failed: {error}")
        status = replace(status, setup=self.setup)
        self._cached = (time.monotonic(), status)
        return self._visible(status)

    def _visible(self, status: ProviderStatus) -> ProviderStatus:
        if allowed(self.id):
            return status
        return replace(status, available=False, detail=OWNER_ONLY, models=[], default_model=None, setup=[])

    def _status(self) -> ProviderStatus:
        raise NotImplementedError

    def complete(self, prompt: str, *, system: str | None = None, model: str | None = None, timeout: float = 180) -> str:
        raise NotImplementedError


def minimal_env(extra: dict | None = None) -> dict:
    env = {key: os.environ[key] for key in PASSTHROUGH_ENV if key in os.environ}
    return {**env, **(extra or {})}


def run_cli(args: list[str], *, stdin: str, timeout: float, cwd: str) -> subprocess.CompletedProcess:
    if shutil.which(args[0]) is None:
        raise LLMError(f"`{args[0]}` is not installed on this machine.")
    try:
        return subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=timeout,
                              cwd=cwd, env=minimal_env(), check=False)
    except subprocess.TimeoutExpired:
        raise LLMError(f"`{args[0]}` did not answer within {timeout:g} seconds.") from None


def scratch_dir():
    return tempfile.TemporaryDirectory(prefix="skillforge-llm-")


FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str):
    """Pull the first JSON object out of a model reply (tolerates ``` fences and chatter)."""
    candidates = [match.group(1) for match in FENCE.finditer(text)] + [text]
    for candidate in candidates:
        start = candidate.find("{")
        while start != -1:
            try:
                value, _ = json.JSONDecoder().raw_decode(candidate[start:])
                if isinstance(value, dict):
                    return value
            except ValueError:
                pass
            start = candidate.find("{", start + 1)
    raise ValueError("The reply did not contain a JSON object.")


def complete_json(provider: Provider, prompt: str, *, system: str, model: str | None = None, timeout: float = 180) -> dict:
    """Ask for a JSON object; on unparseable output, retry once with the parse error."""
    reply = provider.complete(prompt, system=system, model=model, timeout=timeout)
    try:
        return extract_json(reply)
    except ValueError:
        retry = (f"{prompt}\n\nYour previous reply was not a valid JSON object. "
                 "Reply with ONLY the JSON object, no prose and no code fences.")
        return extract_json(provider.complete(retry, system=system, model=model, timeout=timeout))
