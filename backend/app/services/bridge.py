"""Run a visitor's Claude Code and Codex on the visitor's own computer.

A visitor pairs their computer once (Studio → Connect): the server makes a random connector token (sfc_...) for
their workspace and stores only its SHA-256. The small program they run (app/connector_client.py) keeps asking the
server for work. When that visitor's chat needs Claude or Codex, the call becomes a job for their computer, where
their own logged-in CLI runs it with no tools (Claude) or a read-only sandbox (Codex) in an empty folder, and the
answer comes back. The server's own logins are never used for visitors.

Jobs are relayed in memory: one server process (a single Render instance) holds the queue. A job nobody picks up
within its time limit fails with a message telling the visitor to start their connector.
"""

import hashlib
import secrets
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field

from app.llm.base import BRIDGED, LLMError, ProviderStatus

PREFIX = "sfc_"
ONLINE_SECONDS = 60  # the program asks for work every ~25 s; a minute of silence means it stopped
MAX_PROMPT = 400_000
MAX_REPLY = 400_000
LABELS = {"claude": "Claude (your computer)", "codex": "Codex (your computer)"}
NOT_CONNECTED = ("Connect your own {name} from your computer: Studio → Connect your Claude / Codex. "
                 "It runs on your login, on your machine.")


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_token() -> str:
    return PREFIX + secrets.token_urlsafe(32)


@dataclass
class Job:
    provider: str
    prompt: str
    system: str | None
    model: str | None
    timeout: float
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    done: threading.Event = field(default_factory=threading.Event)
    taken: bool = False
    text: str | None = None
    error: str | None = None

    def public(self):
        return {"id": self.id, "provider": self.provider, "prompt": self.prompt, "system": self.system,
                "model": self.model, "timeout": self.timeout}


class Relay:
    def __init__(self, clock=time.monotonic, grace=30.0):
        self.clock = clock
        self.grace = grace  # extra wait past the CLI's own limit, for the round trip
        self.lock = threading.Lock()
        self.queues: dict = {}   # workspace -> deque[Job]
        self.jobs: dict = {}     # job id -> (workspace, Job)
        self.offers: dict = {}   # workspace -> {provider: offer}
        self.seen: dict = {}     # workspace -> last contact

    def hello(self, workspace, offers: list[dict]):
        """The program says which CLIs it has and whether they're logged in."""
        clean = {}
        for offer in offers[:4]:
            provider = offer.get("id")
            if provider in BRIDGED:
                clean[provider] = {
                    "available": bool(offer.get("available")),
                    "detail": str(offer.get("detail") or "")[:200],
                    "models": [str(m)[:80] for m in (offer.get("models") or [])][:12],
                    "default_model": (str(offer["default_model"])[:80] if offer.get("default_model") else None),
                }
        with self.lock:
            self.offers[workspace] = clean
            self.seen[workspace] = self.clock()

    def online(self, workspace) -> bool:
        with self.lock:
            return workspace in self.offers and self.clock() - self.seen.get(workspace, -1e9) < ONLINE_SECONDS

    def offer(self, workspace, provider):
        with self.lock:
            return (self.offers.get(workspace) or {}).get(provider)

    def connected(self, workspace) -> list[str]:
        """The providers this workspace's computer can run right now."""
        if not self.online(workspace):
            return []
        with self.lock:
            return [p for p, offer in (self.offers.get(workspace) or {}).items() if offer["available"]]

    def take(self, workspace):
        """The next job for this workspace's computer, if any (and a sign of life)."""
        with self.lock:
            self.seen[workspace] = self.clock()
            queue = self.queues.get(workspace)
            while queue:
                job = queue.popleft()
                if not job.done.is_set():
                    job.taken = True
                    return job
            return None

    def needs_hello(self, workspace) -> bool:
        with self.lock:
            return workspace not in self.offers

    def finish(self, workspace, job_id, text=None, error=None) -> bool:
        with self.lock:
            owner, job = self.jobs.get(job_id, (None, None))
            if job is None or owner != workspace or job.done.is_set():
                return False
            job.text = None if text is None else str(text)[:MAX_REPLY]
            job.error = None if error is None else str(error)[:500]
            job.done.set()
            return True

    def submit(self, workspace, provider, prompt, *, system=None, model=None, timeout=180.0) -> str:
        """Hand a model call to the workspace's computer and wait for the answer (blocks this thread)."""
        if not self.online(workspace):
            raise LLMError(NOT_CONNECTED.format(name=LABELS[provider].split(" ")[0]))
        if len(prompt) > MAX_PROMPT:
            raise LLMError("This request is too large to send to your computer.")
        job = Job(provider=provider, prompt=prompt, system=system, model=model, timeout=float(timeout))
        with self.lock:
            self.queues.setdefault(workspace, deque()).append(job)
            self.jobs[job.id] = (workspace, job)
        try:
            if not job.done.wait(timeout + self.grace):
                raise LLMError(f"{LABELS[provider]} didn't answer in time. Is the connector still running?")
            if job.error:
                raise LLMError(f"{LABELS[provider]}: {job.error}")
            return job.text or ""
        finally:
            with self.lock:
                job.done.set()
                self.jobs.pop(job.id, None)

    def forget(self, workspace):
        with self.lock:
            self.offers.pop(workspace, None)
            self.seen.pop(workspace, None)
            for job in self.queues.pop(workspace, deque()):
                job.error = "The connector was disconnected."
                job.done.set()


relay = Relay()


class WorkspaceBridge:
    """What a visitor's request or chat turn sees for Claude and Codex: their own computer, or nothing."""

    def __init__(self, workspace, relay_=None):
        self.workspace = workspace
        self.relay = relay_ or relay

    def connected(self) -> list[str]:
        return self.relay.connected(self.workspace)

    def status(self, provider) -> ProviderStatus:
        offer = self.relay.offer(self.workspace, provider.id) if self.relay.online(self.workspace) else None
        label = LABELS[provider.id]
        if offer is None:
            return ProviderStatus(provider.id, label, "connector", False,
                                  NOT_CONNECTED.format(name=label.split(" ")[0]))
        if not offer["available"]:
            return ProviderStatus(provider.id, label, "connector", False,
                                  f"Your connector is running, but: {offer['detail'] or 'this CLI is not ready.'}")
        return ProviderStatus(provider.id, label, "connector", True, "Running on your computer, with your login.",
                              offer["models"], offer["default_model"])

    def complete(self, provider_id, prompt, *, system=None, model=None, timeout=180):
        return self.relay.submit(self.workspace, provider_id, prompt, system=system, model=model, timeout=timeout)
