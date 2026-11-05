"""Sandbox child: runs one skill and prints a JSON result to stdout.

Started by runner.py as `python -I -S child.py` with an empty environment, so it
cannot see site-packages, app settings or secrets. Reads one JSON request on stdin.
"""

import base64
import json
import os
import resource
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from policy import ENTRYPOINT, SAFE_BUILTIN_NAMES, check_source  # noqa: E402
from tools import make_tools  # noqa: E402

MAX_OUTPUT_BYTES = 2_000_000

# Runtime guard (defense in depth behind the static policy): once a skill is about to run, these audit
# events raise PermissionError. Audit hooks cannot be removed, so nothing the skill does can undo this.
BLOCKED_EVENTS = (
    "socket.", "ssl.", "urllib.", "http.client.", "ftplib.", "smtplib.", "imaplib.", "poplib.", "nntplib.",
    "telnetlib.", "webbrowser.", "subprocess.", "os.system", "os.exec", "os.spawn", "os.posix_spawn",
    "os.fork", "os.forkpty", "os.kill", "os.killpg", "os.startfile", "pty.", "ctypes.", "cffi.",
    "os.remove", "os.unlink", "os.rename", "os.rmdir", "os.mkdir", "os.makedirs", "os.chmod", "os.chown",
    "os.symlink", "os.link", "os.truncate", "os.utime", "os.chdir", "os.listdir", "os.scandir",
    "os.putenv", "os.unsetenv", "shutil.", "glob.", "fcntl.", "mmap.", "resource.setrlimit",
    "sys.settrace", "sys.setprofile", "code.__new__", "pickle.find_class",
)
# Matched exactly: the stdlib calls sys._getframemodulename, which is harmless.
BLOCKED_EXACT = frozenset({"sys._getframe"})
# Python may still read its own standard library (a lazy import inside a tool); nothing else.
READABLE_ROOTS = tuple({os.path.realpath(sys.base_prefix), os.path.realpath(sys.prefix)})


def blocked(event, args):
    if event in BLOCKED_EXACT or event.startswith(BLOCKED_EVENTS):
        return True
    if event == "open":
        path, mode = args[0], args[1] if len(args) > 1 else "r"
        writing = isinstance(mode, str) and any(flag in mode for flag in "wax+")
        if isinstance(args[2] if len(args) > 2 else None, int):
            writing = writing or bool(args[2] & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC))
        if writing or not isinstance(path, str | bytes):
            return True
        real = os.path.realpath(os.fsdecode(path))
        return not real.startswith(READABLE_ROOTS)
    return False


def install_guard():
    def guard(event, args):
        if blocked(event, args):
            raise PermissionError(f"The sandbox does not allow {event}.")
    sys.addaudithook(guard)


def limit_resources(cpu_seconds):
    limits = [
        (resource.RLIMIT_CPU, cpu_seconds),
        (resource.RLIMIT_FSIZE, 0),  # no file writes
        (resource.RLIMIT_NOFILE, 16),  # stdin, stdout, stderr and a few internals
    ]
    if hasattr(resource, "RLIMIT_NPROC") and sys.platform.startswith("linux"):
        limits.append((resource.RLIMIT_NPROC, 0))  # no new processes
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
    install_guard()

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
