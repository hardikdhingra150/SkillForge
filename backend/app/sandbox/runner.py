"""Run skill source in an isolated child process."""

import base64
import json
import math
import signal
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.sandbox.policy import check_source

SANDBOX_DIR = Path(__file__).resolve().parent
CHILD = SANDBOX_DIR / "child.py"
DEFAULT_TIMEOUT = 10.0
# Starting a container takes time that is not the skill's.
DOCKER_STARTUP_SECONDS = 15.0


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    output: dict | None = None
    error: dict | None = None
    duration_ms: float = 0.0


def docker_command(name: str, image: str) -> list[str]:
    """A throwaway container: no network, read-only root, no capabilities, an unprivileged user, small limits."""
    return [
        "docker", "run", "--rm", "-i", "--name", name,
        "--network", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "--pids-limit", "32",
        "--memory", "256m", "--memory-swap", "256m",
        "--cpus", "1",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--volume", f"{SANDBOX_DIR}:/sandbox:ro",
        "--workdir", "/sandbox",
        image, "python", "-I", "-S", "/sandbox/child.py",
    ]


def start(request: bytes, timeout: float, backend: str):
    if backend == "docker":
        name = f"skillforge-sandbox-{uuid.uuid4().hex[:12]}"
        try:
            return subprocess.run(docker_command(name, settings.sandbox_image), input=request, capture_output=True,
                                  timeout=timeout + DOCKER_STARTUP_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True, check=False)
            raise
    with tempfile.TemporaryDirectory(prefix="skillforge-sandbox-") as workdir:
        return subprocess.run(
            [sys.executable, "-I", "-S", str(CHILD)],
            input=request, capture_output=True, timeout=timeout, env={}, cwd=workdir, check=False,
        )


def run_skill(source: str, *, inputs: dict, files: dict[str, bytes], tools, timeout: float = DEFAULT_TIMEOUT,
              backend: str | None = None) -> SandboxResult:
    """Check the source, then run `run(inputs, tools)` in a child process or a throwaway container.

    The child gets no environment variables, no site-packages, a CPU limit, no
    file writes, a runtime audit guard, and only the tools listed. Raises
    PolicyViolation before starting anything if the source breaks the static policy.
    """
    check_source(source)
    request = json.dumps({
        "source": source,
        "inputs": inputs,
        "files": {name: base64.b64encode(data).decode() for name, data in files.items()},
        "tools": list(tools),
        # CPU limit is a backstop one second past the wall-clock timeout.
        "cpu_seconds": math.ceil(timeout) + 1,
    }).encode()
    try:
        done = start(request, timeout, backend or settings.sandbox_backend)
    except subprocess.TimeoutExpired:
        return SandboxResult(ok=False, error={"type": "Timeout", "message": f"The skill ran longer than {timeout:g} seconds."},
                             duration_ms=timeout * 1000)
    if done.returncode in (-signal.SIGXCPU, -signal.SIGKILL):
        return SandboxResult(ok=False, error={"type": "Timeout", "message": "The skill exceeded its CPU time limit."},
                             duration_ms=timeout * 1000)
    # Docker reports a killed container as 128 + signal; SIGKILL there can also be the memory limit.
    if done.returncode in (128 + signal.SIGXCPU, 128 + signal.SIGKILL):
        return SandboxResult(ok=False, error={"type": "Timeout", "message": "The skill exceeded its CPU time or memory limit."},
                             duration_ms=timeout * 1000)
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        detail = done.stderr.decode(errors="replace").strip().splitlines()[-1:] or [f"exit code {done.returncode}"]
        return SandboxResult(ok=False, error={"type": "SandboxCrash", "message": detail[0][:500]})
    return SandboxResult(ok=reply["ok"], output=reply.get("output"), error=reply.get("error"),
                         duration_ms=reply.get("duration_ms", 0.0))
