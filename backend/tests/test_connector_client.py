import importlib.util
import ssl
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location("connector_client", Path(__file__).parents[1] / "app/connector_client.py")
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


class TlsTests(unittest.TestCase):
    def test_python_without_certificates_falls_back_to_the_systems_and_still_verifies(self):
        context = mock.Mock(verify_mode=ssl.CERT_REQUIRED)
        context.cert_store_stats.return_value = {"x509_ca": 0}
        with mock.patch.object(client.ssl, "create_default_context", return_value=context), \
                mock.patch.dict("sys.modules", {"certifi": None}), \
                mock.patch.object(client.os.path, "exists", side_effect=lambda p: p == "/etc/ssl/cert.pem"):
            self.assertIs(client.tls_context(), context)
        context.load_verify_locations.assert_called_once_with(cafile="/etc/ssl/cert.pem")

    def test_python_with_certificates_is_left_alone(self):
        context = mock.Mock()
        context.cert_store_stats.return_value = {"x509_ca": 120}
        with mock.patch.object(client.ssl, "create_default_context", return_value=context):
            client.tls_context()
        context.load_verify_locations.assert_not_called()


class SafetyTests(unittest.TestCase):
    def test_claude_runs_with_every_tool_off_in_an_empty_folder(self):
        done = mock.Mock(stdout='{"result": "ok"}', stderr="", returncode=0)
        with mock.patch.object(client.subprocess, "run", return_value=done) as run:
            self.assertEqual(client.run_claude({"prompt": "hi", "timeout": 5}), "ok")
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("skillforge-", run.call_args.kwargs["cwd"])
        self.assertNotIn("DATABASE_URL", run.call_args.kwargs["env"])

    def test_codex_runs_in_its_read_only_sandbox(self):
        done = mock.Mock(stdout="", stderr="boom", returncode=1)
        with mock.patch.object(client.subprocess, "run", return_value=done) as run, self.assertRaises(RuntimeError):
            client.run_codex({"prompt": "hi", "timeout": 5})
        args = run.call_args.args[0]
        self.assertEqual(args[args.index("-s") + 1], "read-only")
