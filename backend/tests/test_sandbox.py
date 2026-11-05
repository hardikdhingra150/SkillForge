import unittest

from app.sandbox import PolicyViolation, check_source, run_skill


def skill(body: str) -> str:
    return "def run(inputs, tools):\n" + "".join(f"    {line}\n" for line in body.splitlines())


class PolicyTests(unittest.TestCase):
    def assert_blocked(self, source, fragment):
        with self.assertRaises(PolicyViolation) as caught:
            check_source(source)
        self.assertIn(fragment, str(caught.exception))

    def test_blocks_imports(self):
        self.assert_blocked("import os\n" + skill("return {}"), "Import")
        self.assert_blocked("from pathlib import Path\n" + skill("return {}"), "ImportFrom")

    def test_blocks_dangerous_names(self):
        for name in ("open('x')", "eval('1')", "__import__('os')", "getattr(tools, 'x')", "globals()"):
            with self.subTest(name=name):
                self.assert_blocked(skill(f"return {name}"), "not allowed")

    def test_blocks_dunder_escapes(self):
        self.assert_blocked(skill("return ().__class__.__bases__"), "Private attribute")
        self.assert_blocked(skill("return tools._secret"), "Private attribute")

    def test_blocks_code_running_at_import(self):
        self.assert_blocked("x = [1]\n" + skill("return {}"), "module level")
        self.assert_blocked("class A:\n    pass\n" + skill("return {}"), "ClassDef")

    def test_requires_entrypoint_signature(self):
        self.assert_blocked("def main(inputs, tools):\n    return {}\n", "must define run")
        self.assert_blocked("def run(inputs):\n    return {}\n", "exactly (inputs, tools)")

    def test_rejects_syntax_errors_and_empty_source(self):
        self.assert_blocked("def run(inputs, tools)\n    return {}", "syntax error")
        self.assert_blocked("   ", "empty")


class RunnerTests(unittest.TestCase):
    def test_runs_with_granted_tools_only(self):
        result = run_skill(
            skill("h, rows = tools.read_csv('f')\nreturn {'n': len(rows)}"),
            inputs={}, files={"f": b"a,b\nx,1\ny,2\n"}, tools=["read_csv"],
        )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output, {"n": 2})

    def test_ungranted_tool_names_the_contract(self):
        result = run_skill(skill("return tools.read_csv('f')"), inputs={}, files={}, tools=[])
        self.assertFalse(result.ok)
        self.assertIn("not in this skill's contract", result.error["message"])

    def test_missing_column_lists_available_headers(self):
        result = run_skill(
            skill("h, r = tools.read_csv('f')\nreturn {'v': tools.column(h, r, 'revenue')}"),
            inputs={}, files={"f": b"Product,Sales\nA,1\n"}, tools=["read_csv", "column"],
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.error["code"], "MISSING_COLUMN")
        self.assertEqual(result.error["details"], {"column": "revenue", "available": ["Product", "Sales"]})
        self.assertIn("Available columns: Product, Sales", result.error["message"])

    def test_bad_number_carries_a_code_and_parse_amount_handles_exports(self):
        files = {"f": b"P,S\nA,$1,200.50\n".replace(b"$1,200.50", b'"$1,200.50"')}
        strict = run_skill(skill("h, r = tools.read_csv('f')\nreturn {'v': str(tools.to_decimal(tools.column(h, r, 'S')[0]))}"),
                           inputs={}, files=files, tools=["read_csv", "column", "to_decimal"])
        self.assertEqual((strict.error["code"], strict.error["details"]), ("BAD_NUMBER", {"value": "$1,200.50"}))
        lenient = run_skill(skill("h, r = tools.read_csv('f')\nreturn {'v': str(tools.parse_amount(tools.column(h, r, 'S')[0]))}"),
                            inputs={}, files=files, tools=["read_csv", "column", "parse_amount"])
        self.assertEqual(lenient.output, {"v": "1200.50"})

    def test_infinite_loop_times_out(self):
        result = run_skill(skill("while True:\n    pass"), inputs={}, files={}, tools=[], timeout=1.5)
        self.assertFalse(result.ok)
        self.assertEqual(result.error["type"], "Timeout")

    def test_output_must_be_a_json_dict(self):
        self.assertEqual(run_skill(skill("return [1]"), inputs={}, files={}, tools=[]).error["type"], "TypeError")
        self.assertFalse(run_skill(skill("return {'x': float('nan')}"), inputs={}, files={}, tools=[]).ok)

    def test_policy_violation_never_starts_a_process(self):
        with self.assertRaises(PolicyViolation):
            run_skill("import os\n" + skill("return {}"), inputs={}, files={}, tools=[])


if __name__ == "__main__":
    unittest.main()


class RuntimeGuardTests(unittest.TestCase):
    """The child's audit hook blocks escapes even if code got past the static policy."""

    ESCAPES = {
        "network": "import socket; socket.create_connection(('example.com', 80), timeout=1)",
        "write a file": "open('escape.txt', 'w').write('x')",
        "read a file": "open('/etc/hosts').read()",
        "list a directory": "import os; os.listdir('/')",
        "start a process": "import subprocess; subprocess.run(['true'])",
        "shell out": "import os; os.system('true')",
        "native code": "import ctypes; ctypes.CDLL(None)",
        "change environment": "import os; os.putenv('X', '1')",
    }

    def attempt(self, code):
        import subprocess
        import sys
        from pathlib import Path

        sandbox = Path(__file__).resolve().parents[1] / "app" / "sandbox"
        script = f"import sys; sys.path.insert(0, {str(sandbox)!r}); import child; child.install_guard()\n" \
                 f"try:\n    {code}\n    print('ALLOWED')\nexcept PermissionError as error:\n    print('BLOCKED', error)\n"
        done = subprocess.run([sys.executable, "-I", "-S", "-c", script], capture_output=True, text=True, timeout=20)
        return done.stdout.strip() or done.stderr.strip().splitlines()[-1]

    def test_escapes_are_blocked(self):
        for name, code in self.ESCAPES.items():
            with self.subTest(name):
                self.assertTrue(self.attempt(code).startswith("BLOCKED"), self.attempt(code))

    def test_stdlib_imports_still_work(self):
        self.assertEqual(self.attempt("import statistics; statistics.mean([1, 2])"), "ALLOWED")


def docker_ready(image):
    import shutil
    import subprocess
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "image", "inspect", image], capture_output=True, check=False).returncode == 0


class DockerBackendTests(unittest.TestCase):
    def test_container_is_locked_down(self):
        from app.sandbox.runner import docker_command
        command = docker_command("skillforge-sandbox-test", "python:3.14-slim")
        joined = " ".join(command)
        for flag in ("--rm", "--network none", "--read-only", "--cap-drop ALL", "--security-opt no-new-privileges",
                     "--user 65534:65534", "--pids-limit 32", "--memory 256m"):
            self.assertIn(flag, joined)
        self.assertTrue(joined.endswith("python:3.14-slim python -I -S /sandbox/child.py"))
        self.assertRegex(joined, r"--volume \S+/app/sandbox:/sandbox:ro")


@unittest.skipUnless(docker_ready("python:3.14-slim"), "Docker and the python:3.14-slim image are needed")
class DockerRunTests(unittest.TestCase):
    def test_skill_runs_in_a_container(self):
        result = run_skill(
            skill("h, rows = tools.read_csv('f')\nreturn {'n': len(rows)}"),
            inputs={}, files={"f": b"a,b\nx,1\ny,2\n"}, tools=["read_csv"], backend="docker",
        )
        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.output, {"n": 2})

    def test_infinite_loop_times_out_in_a_container(self):
        result = run_skill(skill("while True:\n    pass"), inputs={}, files={}, tools=[], timeout=1.5, backend="docker")
        self.assertFalse(result.ok)
        self.assertEqual(result.error["type"], "Timeout")

    def test_container_has_no_network(self):
        import subprocess

        from app.sandbox.runner import docker_command
        command = docker_command("skillforge-sandbox-net", "python:3.14-slim")
        command[-4:] = ["python", "-c", "import socket; socket.create_connection(('1.1.1.1', 53), timeout=2)"]
        done = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
        self.assertNotEqual(done.returncode, 0)
        self.assertRegex(done.stderr, r"OSError|unreachable|Network")
