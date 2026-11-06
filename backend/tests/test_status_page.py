import unittest
from unittest import mock

from fastapi.testclient import TestClient

from app.main import app


class StatusPageTests(unittest.TestCase):
    def test_the_bare_address_says_it_is_running_and_links_onward(self):
        with mock.patch("app.main.settings.frontend_origins", ["https://skillforge.example"]):
            response = TestClient(app).get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        for text in ("SkillForge API", "Running", "/api/v1/health/ready", "/docs", 'href="https://skillforge.example"'):
            self.assertIn(text, response.text)

    def test_no_website_link_without_an_https_site(self):
        with mock.patch("app.main.settings.frontend_origins", ["http://localhost:5173"]):
            self.assertNotIn("Open SkillForge", TestClient(app).get("/").text)
