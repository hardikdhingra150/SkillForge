import unittest

from fastapi.testclient import TestClient

from app.main import app


class LocalHostTests(unittest.TestCase):
    def test_rejects_non_loopback_host(self):
        client = TestClient(app)
        self.assertEqual(client.get("/api/v1/health/live", headers={"Host": "example.invalid:8000"}).status_code, 400)

    def test_allows_loopback_hosts(self):
        client = TestClient(app)
        for host in ("localhost:8000", "127.0.0.1:8000"):
            with self.subTest(host=host):
                self.assertEqual(client.get("/api/v1/health/live", headers={"Host": host}).status_code, 200)
