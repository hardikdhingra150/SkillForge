import unittest
from unittest import mock

from app.services import retention


class FakeBegin:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, *exc):
        return False


class RetentionTests(unittest.TestCase):
    def test_nothing_to_delete_runs_no_deletes(self):
        db = mock.Mock()
        self.assertEqual(retention.delete_workspaces(db, []), 0)
        db.execute.assert_not_called()

    def test_deletes_children_before_the_workspace(self):
        db = mock.Mock()
        db.execute.return_value.rowcount = 2
        self.assertEqual(retention.delete_workspaces(db, ["a", "b"]), 2)
        tables = [call.args[0].table.name for call in db.execute.call_args_list]
        self.assertEqual(tables, ["execution_events", "executions", "tasks", "conversations", "audit_events",
                                  "skill_versions", "workspaces"])

    def test_cleans_up_in_batches_until_a_short_one(self):
        factory = mock.Mock()
        factory.begin.side_effect = lambda: FakeBegin(mock.Mock())
        with mock.patch.object(retention, "idle_workspaces", return_value=["w"]), \
                mock.patch.object(retention, "delete_workspaces", side_effect=[retention.BATCH, 3]):
            self.assertEqual(retention.clean_up(factory, 30), retention.BATCH + 3)
