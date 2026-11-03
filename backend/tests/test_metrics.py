import unittest

from app.api.metrics import Run, chat_run, summarize, workbench_run


class MetricsTests(unittest.TestCase):
    def test_workbench_runs(self):
        self.assertEqual(workbench_run("succeeded", {"skill": {"repaired_from": "1.0.0"}}, 2.0).events, ("repaired",))
        self.assertEqual(workbench_run("succeeded", {"skill": {"id": "x"}}, 1.0).events, ("reused",))
        self.assertFalse(workbench_run("waiting_approval", {}, None).ok)

    def test_chat_replies_count_only_skill_work(self):
        self.assertIsNone(chat_run("done", None, 3.0))                                    # a direct answer
        self.assertIsNone(chat_run("done", {"event": "clarify", "question": "?"}, 1.0))   # a question
        self.assertEqual(chat_run("done", {"event": "created"}, 9.0).events, ("created",))
        pipeline = {"event": "pipeline", "steps": [{"event": "reused"}, {"event": "created"}]}
        self.assertEqual(chat_run("done", pipeline, 5.0).events, ("reused", "created"))
        self.assertFalse(chat_run("failed", None, 4.0).ok)

    def test_summary(self):
        runs = [Run(True, 2.0, ("reused",)), Run(True, 4.0, ("created",)), Run(False, 30.0, ()), Run(True, None, ("reused",))]
        self.assertEqual(summarize(runs, skills=7, repaired_versions=1), {
            "skills": 7, "runs": 4, "succeeded": 3, "success_rate": 75.0, "repairs": 1,
            "reuses": 2, "created": 1, "average_seconds": 3.0,
        })

    def test_empty_workspace(self):
        summary = summarize([], 0, 0)
        self.assertIsNone(summary["success_rate"])
        self.assertIsNone(summary["average_seconds"])


if __name__ == "__main__":
    unittest.main()
