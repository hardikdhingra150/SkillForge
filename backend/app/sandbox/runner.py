"""Run skill source in an isolated child process."""

import base64
import json
import math
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.sandbox.policy import check_source

CHILD = Path(__file__).resolve().parent / "child.py"
DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True)
class SandboxResult:
    ok: bool
    output: dict | None = None
    error: dict | None = None
    duration_ms: float = 0.0


def run_skill(source: str, *, inputs: dict, files: dict[str, bytes], tools, timeout: float = DEFAULT_TIMEOUT) -> SandboxResult:
    """Check the source, then run `run(inputs, tools)` in a child process.

    The child gets no environment variables, no site-packages, a CPU limit, no
    file writes, and only the tools listed. Raises PolicyViolation before
    starting a process if the source breaks the static policy.
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
    with tempfile.TemporaryDirectory(prefix="skillforge-sandbox-") as workdir:
        try:
            done = subprocess.run(
                [sys.executable, "-I", "-S", str(CHILD)],
                input=request, capture_output=True, timeout=timeout, env={}, cwd=workdir, check=False,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(ok=False, error={"type": "Timeout", "message": f"The skill ran longer than {timeout:g} seconds."},
                                 duration_ms=timeout * 1000)
    if done.returncode in (-signal.SIGXCPU, -signal.SIGKILL):
        return SandboxResult(ok=False, error={"type": "Timeout", "message": "The skill exceeded its CPU time limit."},
                             duration_ms=timeout * 1000)
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        detail = done.stderr.decode(errors="replace").strip().splitlines()[-1:] or [f"exit code {done.returncode}"]
        return SandboxResult(ok=False, error={"type": "SandboxCrash", "message": detail[0][:500]})
    return SandboxResult(ok=reply["ok"], output=reply.get("output"), error=reply.get("error"),
                         duration_ms=reply.get("duration_ms", 0.0))
