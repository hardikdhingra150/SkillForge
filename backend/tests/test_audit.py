import unittest

from app.services.audit import record, skill_target


class FakeSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)


class AuditRecordTests(unittest.TestCase):
    def test_records_into_the_callers_transaction(self):
        db = FakeSession()
        event = record(db, actor="api-token", action="skill.retired", target=skill_target("slugify", "1.0.0"),
                       reason="Broke on unicode titles.", details={"replaced_by": "1.0.1"})
        self.assertEqual(db.added, [event])
        self.assertEqual((event.actor, event.action, event.target), ("api-token", "skill.retired", "slugify@1.0.0"))
        self.assertEqual(event.details_json, {"replaced_by": "1.0.1"})

    def test_missing_reason_and_long_values_are_bounded(self):
        event = record(FakeSession(), actor="x" * 99, action="run.rejected", target="t" * 999, reason="")
        self.assertEqual((len(event.actor), len(event.target), event.reason), (40, 160, "No reason given."))


if __name__ == "__main__":
    unittest.main()
