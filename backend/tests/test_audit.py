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


class AuditEndpointTests(unittest.TestCase):
    def test_unknown_actions_are_rejected_before_querying(self):
        from fastapi.testclient import TestClient

        from app.database.session import get_db
        from app.main import app

        app.dependency_overrides[get_db] = lambda: None
        try:
            response = TestClient(app).get("/api/v1/audit?action=skill.deleted")
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 422)
        self.assertIn("skill.promoted", response.json()["detail"])
