import threading
import unittest
from unittest import mock
from uuid import uuid4

from app.llm import LLMError, bridged
from app.llm.registry import ClaudeCLI, CodexCLI
from app.services.bridge import Relay, WorkspaceBridge

CLAUDE = {"id": "claude", "available": True, "detail": "Logged in.", "models": ["default", "opus"],
          "default_model": "default"}


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.relay = Relay()
        self.workspace = uuid4()

    def test_a_job_goes_to_the_computer_and_its_answer_comes_back(self):
        self.relay.hello(self.workspace, [CLAUDE])
        answers = []
        caller = threading.Thread(target=lambda: answers.append(
            self.relay.submit(self.workspace, "claude", "Say hi", system="Be brief.", timeout=5)))
        caller.start()
        for _ in range(100):
            job = self.relay.take(self.workspace)
            if job:
                break
            threading.Event().wait(0.01)
        self.assertEqual((job.provider, job.prompt, job.system), ("claude", "Say hi", "Be brief."))
        self.assertTrue(self.relay.finish(self.workspace, job.id, text="hi"))
        caller.join(5)
        self.assertEqual(answers, ["hi"])

    def test_another_workspace_cannot_answer_or_take_the_job(self):
        relay = Relay(grace=0)
        relay.hello(self.workspace, [CLAUDE])
        other, result = uuid4(), {}

        def ask():
            try:
                relay.submit(self.workspace, "claude", "secret", timeout=0.3)
            except LLMError as error:
                result["error"] = str(error)
        thread = threading.Thread(target=ask)
        thread.start()
        for _ in range(100):
            if relay.jobs:
                break
            threading.Event().wait(0.005)
        job_id = next(iter(relay.jobs))
        self.assertIsNone(relay.take(other))
        self.assertFalse(relay.finish(other, job_id, text="forged"))
        thread.join(5)
        self.assertIn("didn't answer in time", result["error"])

    def test_offline_computer_says_how_to_connect(self):
        with self.assertRaises(LLMError) as caught:
            self.relay.submit(self.workspace, "codex", "hi")
        self.assertIn("Connect your own Codex", str(caught.exception))

    def test_status_follows_the_computer(self):
        bridge = WorkspaceBridge(self.workspace, self.relay)
        self.assertFalse(bridge.status(ClaudeCLI()).available)
        self.relay.hello(self.workspace, [CLAUDE, {"id": "codex", "available": False, "detail": "Not logged in."}])
        claude, codex = bridge.status(ClaudeCLI()), bridge.status(CodexCLI())
        self.assertTrue(claude.available)
        self.assertEqual(claude.models, ["default", "opus"])
        self.assertFalse(codex.available)
        self.assertIn("Not logged in", codex.detail)
        self.assertEqual(bridge.connected(), ["claude"])

    def test_unknown_providers_from_the_computer_are_ignored(self):
        self.relay.hello(self.workspace, [{"id": "rm -rf", "available": True}])
        self.assertEqual(self.relay.connected(self.workspace), [])


class NeverTheServersLoginTests(unittest.TestCase):
    def test_a_visitors_claude_and_codex_calls_go_to_their_computer(self):
        bridge = mock.Mock()
        bridge.complete.return_value = "from the visitor's computer"
        with bridged(bridge), mock.patch("subprocess.run") as run, mock.patch("shutil.which", return_value="/x"):
            self.assertEqual(ClaudeCLI().complete("hi"), "from the visitor's computer")
            self.assertEqual(CodexCLI().complete("hi"), "from the visitor's computer")
            ClaudeCLI().status(refresh=True)
        run.assert_not_called()
        self.assertEqual(bridge.complete.call_count, 2)
