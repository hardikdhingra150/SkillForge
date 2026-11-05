import unittest
from unittest import mock

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.security import require_access

TOKEN = "t" * 40

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_access)])


@router.get("/skills")
def skills():
    return {"ok": True}


@router.get("/executions/run/stream")
def stream():
    return {"ok": True}


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def configured(token=None, env="development"):
    return mock.patch.multiple("app.security.settings", api_token=SecretStr(token) if token else None, app_env=env)


class AccessTests(unittest.TestCase):
    def test_development_without_a_token_stays_open(self):
        with configured():
            self.assertEqual(client.get("/api/v1/skills").status_code, 200)

    def test_production_without_a_token_is_closed(self):
        with configured(env="production"):
            response = client.get("/api/v1/skills")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"]["code"], "API_TOKEN_REQUIRED")

    def test_a_configured_token_is_required(self):
        with configured(TOKEN):
            missing = client.get("/api/v1/skills")
            wrong = client.get("/api/v1/skills", headers={"Authorization": "Bearer " + "x" * 40})
            basic = client.get("/api/v1/skills", headers={"Authorization": f"Basic {TOKEN}"})
            right = client.get("/api/v1/skills", headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual([missing.status_code, wrong.status_code, basic.status_code, right.status_code], [401, 401, 401, 200])
        self.assertEqual(missing.headers["WWW-Authenticate"], "Bearer")

    def test_production_with_a_token_works(self):
        with configured(TOKEN, env="production"):
            self.assertEqual(client.get("/api/v1/skills", headers={"Authorization": f"Bearer {TOKEN}"}).status_code, 200)

    def test_only_streams_accept_the_token_in_the_query(self):
        with configured(TOKEN):
            self.assertEqual(client.get(f"/api/v1/executions/run/stream?access_token={TOKEN}").status_code, 200)
            self.assertEqual(client.get(f"/api/v1/skills?access_token={TOKEN}").status_code, 401)

    def test_short_tokens_are_rejected_by_settings(self):
        from pydantic import ValidationError

        from app.config import Settings
        with self.assertRaises(ValidationError):
            Settings(api_token="too-short", postgres_password="x")


if __name__ == "__main__":
    unittest.main()
