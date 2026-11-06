"""SkillForge connector: lets a SkillForge site use the Claude Code or Codex you are logged in to on this computer.

Run it from the command the Studio shows you (Studio -> Connect your Claude / Codex):

    python3 skillforge-connect.py --api https://.../api/v1 sfc_...

While it runs, the site sends your chats' model requests here. This program runs them with your own CLI and sends
the answers back. It only ever starts `claude` or `codex`, always with these limits, so the site can't make it do
anything else:

- Claude Code runs with every tool turned off (no files, no shell, no web), in an empty temporary folder.
- Codex runs in its read-only sandbox, in an empty temporary folder.
- Neither gets this computer's environment variables beyond what it needs to find your login.

Press Ctrl+C to stop. Needs Python 3.8+ and nothing else (standard library only).
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

VERSION = "1"
POLL_SECONDS = 20
HELLO_EVERY = 300
PASSTHROUGH = ("HOME", "PATH", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM", "USERPROFILE",
               "APPDATA", "LOCALAPPDATA", "SYSTEMROOT", "COMSPEC", "PATHEXT", "TEMP", "TMP", "HOMEDRIVE", "HOMEPATH",
               "CLAUDE_CONFIG_DIR", "CODEX_HOME")


def env():
    return {key: os.environ[key] for key in PASSTHROUGH if key in os.environ}


def say(text):
    print(time.strftime("%H:%M:%S"), text, flush=True)


# ---------- the CLIs on this computer ----------

def claude_status():
    path = shutil.which("claude")
    if not path:
        return {"id": "claude", "available": False, "detail": "Claude Code is not installed on the connected computer."}
    try:
        done = subprocess.run([path, "auth", "status"], capture_output=True, text=True, timeout=60, env=env())
        info = json.loads(done.stdout or "{}")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {"id": "claude", "available": False, "detail": "Could not read `claude auth status` on the connected computer."}
    if not info.get("loggedIn"):
        return {"id": "claude", "available": False, "detail": "Not logged in on the connected computer: run `claude auth login`."}
    return {"id": "claude", "available": True, "detail": "Logged in.", "models": ["default", "sonnet", "opus", "haiku"],
            "default_model": "default"}


def codex_status():
    path = shutil.which("codex")
    if not path:
        return {"id": "codex", "available": False, "detail": "Codex is not installed on the connected computer."}
    try:
        done = subprocess.run([path, "login", "status"], capture_output=True, text=True, timeout=60, env=env())
    except (OSError, subprocess.TimeoutExpired):
        return {"id": "codex", "available": False, "detail": "Could not run `codex login status` on the connected computer."}
    text = (done.stdout + done.stderr).strip()
    if done.returncode != 0 or "not logged in" in text.lower():
        return {"id": "codex", "available": False, "detail": "Not logged in on the connected computer: run `codex login`."}
    return {"id": "codex", "available": True, "detail": "Logged in.", "models": ["default"], "default_model": "default"}


def run_claude(job):
    args = [shutil.which("claude") or "claude", "-p", "--output-format", "json", "--tools", "",
            "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"]
    if job.get("system"):
        args += ["--system-prompt", job["system"]]
    if job.get("model") and job["model"] != "default":
        args += ["--model", job["model"]]
    with tempfile.TemporaryDirectory(prefix="skillforge-") as cwd:
        done = subprocess.run(args, input=job["prompt"], capture_output=True, text=True, cwd=cwd, env=env(),
                              timeout=job.get("timeout", 180))
    try:
        reply = json.loads(done.stdout)
    except ValueError:
        raise RuntimeError((done.stderr or done.stdout or "Claude returned no output.").strip()[:400]) from None
    if reply.get("is_error"):
        raise RuntimeError(str(reply.get("result") or reply.get("terminal_reason") or "Claude reported an error.")[:400])
    return reply.get("result", "")


def run_codex(job):
    prompt = f"{job['system']}\n\n---\n\n{job['prompt']}" if job.get("system") else job["prompt"]
    with tempfile.TemporaryDirectory(prefix="skillforge-") as cwd:
        out = os.path.join(cwd, "reply.txt")
        args = [shutil.which("codex") or "codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only",
                "-C", cwd, "-o", out, "--color", "never"]
        if job.get("model") and job["model"] != "default":
            args += ["-m", job["model"]]
        done = subprocess.run([*args, "-"], input=prompt, capture_output=True, text=True, cwd=cwd, env=env(),
                              timeout=job.get("timeout", 180))
        reply = open(out, encoding="utf-8").read().strip() if os.path.exists(out) else ""
    if done.returncode != 0 or not reply:
        lines = (done.stderr or done.stdout or "no reply").strip().splitlines() or ["no reply"]
        raise RuntimeError(f"Codex: {lines[-1][:400]}")
    return reply


RUNNERS = {"claude": run_claude, "codex": run_codex}


# ---------- talking to the site ----------

class Site:
    def __init__(self, api, token):
        self.api = api.rstrip("/")
        self.token = token

    def call(self, method, path, body=None, timeout=30):
        request = urllib.request.Request(
            self.api + path, method=method, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                     "User-Agent": f"skillforge-connect/{VERSION}"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)

    def hello(self):
        offers = [claude_status(), codex_status()]
        self.call("POST", "/connector/hello", {"offers": offers})
        ready = [o["id"] for o in offers if o["available"]]
        for offer in offers:
            say(f"{offer['id']}: {'ready' if offer['available'] else offer['detail']}")
        return ready


def handle(site, job):
    started = time.monotonic()
    name = "Claude" if job["provider"] == "claude" else "Codex"
    say(f"Running a {name} request for SkillForge...")
    try:
        runner = RUNNERS[job["provider"]]
        result = {"text": runner(job)}
        say(f"  done in {time.monotonic() - started:.0f}s.")
    except subprocess.TimeoutExpired:
        result = {"error": f"{name} did not finish within {job.get('timeout', 180):g} seconds."}
        say("  timed out.")
    except Exception as error:  # report every failure back instead of dying
        result = {"error": str(error)[:500] or type(error).__name__}
        say(f"  failed: {result['error']}")
    try:
        site.call("POST", f"/connector/jobs/{job['id']}", result)
    except (urllib.error.URLError, OSError) as error:
        say(f"  couldn't send the answer back: {error}")


def main():
    parser = argparse.ArgumentParser(description="Connect your Claude Code / Codex to a SkillForge site.")
    parser.add_argument("--api", required=True, help="The site's API address, ending in /api/v1")
    parser.add_argument("token", help="The connector token the Studio showed you (sfc_...)")
    args = parser.parse_args()
    if not args.token.startswith("sfc_"):
        sys.exit("That doesn't look like a connector token (it starts with sfc_). Copy the command from the Studio.")
    if not args.api.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        sys.exit("The --api address must start with https://.")

    site = Site(args.api, args.token)
    say(f"SkillForge connector {VERSION}: connecting to {site.api}")
    try:
        ready = site.hello()
    except urllib.error.HTTPError as error:
        sys.exit(f"The site refused this connector ({error.code}). Pair again in the Studio and use the new command.")
    except (urllib.error.URLError, OSError) as error:
        sys.exit(f"Can't reach {site.api}: {error}")
    if not ready:
        say("Neither Claude Code nor Codex is ready on this computer yet. Fix that (see above); this keeps "
            "checking every few minutes. Leave it running.")
    say("Connected. Leave this window open while you use SkillForge. Press Ctrl+C to stop.")

    last_hello, quiet = time.monotonic(), False
    while True:
        try:
            if time.monotonic() - last_hello > HELLO_EVERY:
                site.hello()
                last_hello = time.monotonic()
            status, job = site.call("GET", f"/connector/next?wait={POLL_SECONDS}", timeout=POLL_SECONDS + 15)
            quiet = False
            if status == 200 and job:
                threading.Thread(target=handle, args=(site, job), daemon=True).start()
        except urllib.error.HTTPError as error:
            if error.code == 428:
                site.hello()
                last_hello = time.monotonic()
            elif error.code == 401:
                sys.exit("This connector was replaced or disconnected in the Studio. Pair again to reconnect.")
            else:
                time.sleep(5)
        except (urllib.error.URLError, OSError, ValueError) as error:
            if not quiet:
                say(f"Lost the connection ({error}); retrying. The site may be waking up.")
                quiet = True
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        say("Stopped.")
