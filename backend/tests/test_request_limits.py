import unittest
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.request_limits import RequestSizeLimit


class RequestSizeLimitTests(unittest.TestCase):
    def test_counts_body_bytes_without_content_length_and_replays_small_requests(self):
        app = FastAPI()
        app.add_middleware(RequestSizeLimit)

        @app.post("/")
        async def echo(request: Request):
            return {"body": (await request.body()).decode()}

        client = TestClient(app)
        with patch("app.request_limits.MAX_REQUEST_BYTES", 4):
            self.assertEqual(client.post("/", content=iter([b"ab", b"cd"])).json(), {"body": "abcd"})
            self.assertEqual(client.post("/", content=iter([b"ab", b"cde"])).status_code, 413)
