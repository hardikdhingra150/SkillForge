import asyncio
import json
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from fastapi import FastAPI
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.skills import router
from app.config import settings
from app.database.session import get_db


class SkillRegistryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", poolclass=StaticPool,
            connect_args={"check_same_thread": False},
        )
        with self.engine.begin() as db:
            db.execute(text("""
                CREATE TABLE skill_versions (
                    skill_id TEXT, version TEXT, capability TEXT,
                    status TEXT, implementation_hash TEXT,
                    validation_json JSON, created_at DATETIME,
                    PRIMARY KEY (skill_id, version)
                )
            """))
            for skill_id, version, capability, status in [
                ("revenue_by_product", "1.0.0", "sales_analysis", "validated"),
                ("revenue_by_product", "1.1.0", "sales_analysis", "draft"),
                ("text_summary", "2.0.0", "research", "retired"),
                ("literal_%", "1.0.0", "literal", "draft"),
            ]:
                db.execute(text("""
                    INSERT INTO skill_versions VALUES
                    (:id, :version, :capability, :status, :hash, :validation, :created)
                """), {
                    "id": skill_id, "version": version, "capability": capability,
                    "status": status, "hash": "a" * 64,
                    "validation": json.dumps({"passed": True, "test_count": 4,
                        "tests": [{"name": "fixture", "passed": True}]}),
                    "created": "2026-10-27 00:00:00",
                })
        self.app = FastAPI()
        self.app.include_router(router)

        def database():
            with Session(self.engine) as db:
                yield db

        self.app.dependency_overrides[get_db] = database

    def tearDown(self):
        self.engine.dispose()

    def request(self, params=None, method="GET"):
        async def run():
            messages = []

            async def receive():
                return {"type": "http.request", "body": b"", "more_body": False}

            async def send(message):
                messages.append(message)

            await self.app({
                "type": "http", "asgi": {"version": "3.0"},
                "http_version": "1.1", "method": method, "scheme": "http",
                "path": "/api/v1/skills", "raw_path": b"/api/v1/skills",
                "query_string": urlencode(params or {}).encode(), "headers": [],
                "client": ("127.0.0.1", 1234), "server": ("test", 80),
            }, receive, send)
            status = next(m["status"] for m in messages if m["type"] == "http.response.start")
            body = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
            return status, json.loads(body)

        return asyncio.run(run())

    def test_serializes_actual_registry_metadata(self):
        status, page = self.request({"status": "validated"})
        self.assertEqual(status, 200)
        skill, = page["items"]
        self.assertEqual(skill["skill_id"], "revenue_by_product")
        self.assertEqual(skill["implementation_hash"], "a" * 64)
        self.assertEqual(skill["validation"]["test_count"], 4)
        self.assertTrue(skill["validation"]["tests"][0]["passed"])
        self.assertIn("created_at", skill)
        self.assertNotIn("validation_json", skill)

    def test_composite_cursor_keeps_versions_of_the_same_skill(self):
        pages = []
        cursor = {}
        while True:
            status, page = self.request({"limit": 1, **cursor})
            self.assertEqual(status, 200)
            pages.extend((s["skill_id"], s["version"]) for s in page["items"])
            if not page["has_more"]:
                self.assertIsNone(page["next_after_skill_id"])
                self.assertIsNone(page["next_after_version"])
                break
            cursor = {"after_skill_id": page["next_after_skill_id"], "after_version": page["next_after_version"]}
        self.assertEqual(pages, [("literal_%", "1.0.0"), ("revenue_by_product", "1.0.0"),
                                 ("revenue_by_product", "1.1.0"), ("text_summary", "2.0.0")])

    def test_status_filters(self):
        for value, count in [("validated", 1), ("draft", 2), ("retired", 1)]:
            status, page = self.request({"status": value})
            self.assertEqual(status, 200)
            self.assertEqual(len(page["items"]), count)
            self.assertTrue(all(s["status"] == value for s in page["items"]))

    def test_case_insensitive_search_by_id_capability_and_version(self):
        for query, count in [(" REVENUE ", 2), ("RESEARCH", 1), ("1.1.0", 1)]:
            status, page = self.request({"q": query})
            self.assertEqual(status, 200)
            self.assertEqual(len(page["items"]), count)

    def test_search_wildcards_are_literal(self):
        for query in ["%", "_%", "literal_%"]:
            status, page = self.request({"q": query})
            self.assertEqual(status, 200)
            self.assertEqual([s["skill_id"] for s in page["items"]], ["literal_%"])

    def test_filter_and_search_can_return_empty_page(self):
        status, page = self.request({"q": "revenue", "status": "retired"})
        self.assertEqual(status, 200)
        self.assertEqual(page["items"], [])
        self.assertFalse(page["has_more"])

    def test_cursor_requires_both_fields(self):
        for params in [{"after_skill_id": "revenue_by_product"}, {"after_version": "1.0.0"}]:
            self.assertEqual(self.request(params)[0], 400)

    def test_query_bounds_and_status_validation(self):
        for params in [{"limit": 0}, {"limit": 101}, {"q": "x" * 101},
                       {"status": "unknown"}, {"after_skill_id": ""},
                       {"after_version": "x" * 33}, {"after_skill_id": "x" * 81}]:
            with self.subTest(params=params):
                self.assertEqual(self.request(params)[0], 422)

    def test_existing_development_gate(self):
        with patch.object(settings, "app_env", "production"):
            status, body = self.request()
        self.assertEqual(status, 503)
        self.assertEqual(body["detail"]["code"], "LOCAL_API_DISABLED")

    def test_database_failure_is_retryable_without_internal_details(self):
        failed = Mock()
        failed.scalars.side_effect = SQLAlchemyError("private database diagnostic")
        self.app.dependency_overrides[get_db] = lambda: failed
        with self.assertLogs("uvicorn.error", level="ERROR"):
            status, body = self.request()
        self.assertEqual(status, 503)
        self.assertEqual(body["detail"], "The skill registry is unavailable. Retry shortly.")

    def test_registry_has_no_write_route(self):
        self.assertEqual(self.request(method="POST")[0], 405)
