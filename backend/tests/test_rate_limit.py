import unittest
from unittest import mock

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app import rate_limit
from app.rate_limit import RateLimiter


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class RateLimiterTests(unittest.TestCase):
    def test_sliding_window(self):
        clock = Clock()
        limiter = RateLimiter(clock)
        self.assertEqual([limiter.check(("a", "write"), 3) for _ in range(3)], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(limiter.check(("a", "write"), 3), 60.0)
        self.assertEqual(limiter.check(("b", "write"), 3), 0.0)        # other clients are separate
        clock.now += 30
        self.assertAlmostEqual(limiter.check(("a", "write"), 3), 30.0)
        clock.now += 30
        self.assertEqual(limiter.check(("a", "write"), 3), 0.0)        # the oldest hits left the window


class MiddlewareTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.middleware("http")(rate_limit.rate_limit)
        app.add_middleware(CORSMiddleware, allow_origins=["http://site.test"], allow_methods=["GET", "POST"])

        @app.post("/api/v1/tasks")
        def submit():
            return {"ok": True}

        @app.get("/api/v1/health/live")
        def health():
            return {"ok": True}

        self.client = TestClient(app)
        self.patches = [
            mock.patch.object(rate_limit, "limiter", RateLimiter()),
            mock.patch.multiple("app.rate_limit.settings", rate_limit_writes_per_minute=2, rate_limit_reads_per_minute=2),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in self.patches:
            patch.stop()

    def test_limited_requests_get_429_with_retry_after_and_cors(self):
        headers = {"Origin": "http://site.test"}
        codes = [self.client.post("/api/v1/tasks", headers=headers).status_code for _ in range(2)]
        blocked = self.client.post("/api/v1/tasks", headers=headers)
        self.assertEqual(codes, [200, 200])
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked.json()["detail"]["code"], "RATE_LIMITED")
        self.assertGreater(int(blocked.headers["Retry-After"]), 0)
        self.assertEqual(blocked.headers["access-control-allow-origin"], "http://site.test")

    def test_health_checks_are_exempt(self):
        self.assertEqual({self.client.get("/api/v1/health/live").status_code for _ in range(5)}, {200})


if __name__ == "__main__":
    unittest.main()
