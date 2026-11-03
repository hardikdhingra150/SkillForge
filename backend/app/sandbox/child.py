"""Sandbox child: runs one skill and prints a JSON result to stdout.

Started by runner.py as `python -I -S child.py` with an empty environment, so it
cannot see site-packages, app settings or secrets. Reads one JSON request on stdin.
"""

import base64
import json
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from policy import ENTRYPOINT, SAFE_BUILTIN_NAMES, check_source  # noqa: E402
from tools import make_tools  # noqa: E402

MAX_OUTPUT_BYTES = 2_000_000


def limit_resources(cpu_seconds):
    limits = [
        (resource.RLIMIT_CPU, cpu_seconds),
        (resource.RLIMIT_FSIZE, 0),  # no file writes
    ]
    if hasattr(resource, "RLIMIT_AS") and sys.platform.startswith("linux"):
        limits.append((resource.RLIMIT_AS, 512 * 1024 * 1024))
    for kind, value in limits:
        try:
            resource.setrlimit(kind, (value, value))
        except (ValueError, OSError):
            pass


def reply(payload):
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def main():
    request = json.loads(sys.stdin.buffer.read())
    files = {name: base64.b64decode(data) for name, data in request["files"].items()}
    tools = make_tools(files, request["tools"])
    builtins = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
    safe_builtins = {name: builtins[name] for name in SAFE_BUILTIN_NAMES}

    check_source(request["source"])
    code = compile(request["source"], "<skill>", "exec")
    limit_resources(int(request["cpu_seconds"]))

    started = time.perf_counter()
    try:
        namespace = {"__builtins__": safe_builtins, "__name__": "skill"}
        exec(code, namespace)
        output = namespace[ENTRYPOINT](request["inputs"], tools)
        if not isinstance(output, dict):
            raise TypeError("run must return a dict.")
        if len(json.dumps(output, allow_nan=False)) > MAX_OUTPUT_BYTES:
            raise ValueError("Skill output exceeds 2 MB.")
    except Exception as error:  # every failure is reported, never raised
        detail = {"type": type(error).__name__, "message": str(error)[:500]}
        if getattr(error, "code", None):
            detail.update(code=error.code, details=error.details)
        reply({"ok": False, "error": detail,
               "duration_ms": round((time.perf_counter() - started) * 1000, 2)})
        return
    reply({"ok": True, "output": output, "duration_ms": round((time.perf_counter() - started) * 1000, 2)})


if __name__ == "__main__":
    main()
