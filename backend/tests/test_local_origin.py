import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


class LocalOriginTests(unittest.TestCase):
    def test_rejects_cross_site_form_before_processing_upload(self):
        client = TestClient(app)
        response = client.post(
            f"/api/v1/conversations/{uuid4()}/attachments",
            headers={"Origin": "https://example.invalid"},
            files={"file": ("sample.csv", b"a,b\nc,d\n")},
        )
        self.assertEqual(response.status_code, 403)

    def test_allows_configured_browser_origin_and_non_browser_clients(self):
        client = TestClient(app)
        for headers in ({}, {"Origin": "http://127.0.0.1:5173"}):
            with self.subTest(headers=headers):
                # An empty conversation fails input validation before it can use the database.
                self.assertEqual(client.post("/api/v1/conversations", headers=headers, json={}).status_code, 422)
