import unittest
from unittest import mock
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.security import LOCAL_WORKSPACE_ID, WorkspaceId, require_access, require_operator
from app.services.browser_workspaces import key_hash

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_access)])


@router.get("/whoami")
def whoami(workspace_id: WorkspaceId):
    return {"workspace": str(workspace_id)}


@router.delete("/library", dependencies=[Depends(require_operator)])
def change_library():
    return {"ok": True}


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def browser_mode(token=None):
    return mock.patch.multiple("app.security.settings", auth_mode="browser", app_env="development",
                               api_token=SecretStr(token) if token else None)


def lookup(workspace):
    return (mock.patch("app.services.browser_workspaces.workspace_for", return_value=workspace),
            mock.patch("app.database.session.SessionLocal"))


class BrowserWorkspaceTests(unittest.TestCase):
    def test_off_mode_uses_the_shared_workspace(self):
        with mock.patch.multiple("app.security.settings", auth_mode="off", api_token=None, app_env="development"):
            self.assertEqual(client.get("/api/v1/whoami").json(), {"workspace": str(LOCAL_WORKSPACE_ID)})

    def test_a_browser_without_a_key_is_told_to_get_one(self):
        with browser_mode():
            response = client.get("/api/v1/whoami")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "BROWSER_KEY_NEEDED")

    def test_a_key_selects_its_own_workspace(self):
        workspace = uuid4()
        found, session = lookup(workspace)
        with browser_mode(), found, session:
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer sfb_abc"})
        self.assertEqual(response.json(), {"workspace": str(workspace)})

    def test_an_unknown_key(self):
        found, session = lookup(None)
        with browser_mode(), found, session:
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer sfb_gone"})
        self.assertEqual(response.json()["detail"]["code"], "BROWSER_KEY_UNKNOWN")

    def test_operator_token_still_works(self):
        with browser_mode("o" * 40):
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer " + "o" * 40})
            self.assertEqual(response.json(), {"workspace": str(LOCAL_WORKSPACE_ID)})
            self.assertEqual(client.delete("/api/v1/library", headers={"Authorization": "Bearer " + "o" * 40})
                             .status_code, 200)

    def test_browsers_cannot_change_the_shared_library(self):
        found, session = lookup(uuid4())
        with browser_mode(), found, session:
            response = client.delete("/api/v1/library", headers={"Authorization": "Bearer sfb_abc"})
        self.assertEqual(response.status_code, 403)

    def test_only_the_key_hash_is_stored(self):
        self.assertEqual(len(key_hash("sfb_x")), 64)
        self.assertNotIn("sfb_x", key_hash("sfb_x"))


class DatabaseSettingsTests(unittest.TestCase):
    def test_a_connection_string_replaces_the_password(self):
        settings = Settings(database_url="postgresql://postgres.ref:a-very-long-password-123@pooler.example.com:5432/postgres",
                            postgres_password=None, _env_file=None)
        self.assertEqual(settings.database_password(), "a-very-long-password-123")

    def test_blank_connection_string_is_unset(self):
        self.assertIsNone(Settings(database_url="", postgres_password="x", _env_file=None).database_url)

    def test_some_database_is_required(self):
        with self.assertRaises(ValueError):
            Settings(postgres_password=None, _env_file=None)

    def test_hosted_databases_use_tls(self):
        from app.database import connection

        with mock.patch.object(connection.settings, "database_url",
                               SecretStr("postgresql://u:p@db.example.supabase.co:5432/postgres")):
            url = connection.build_url()
        self.assertEqual(url.query["sslmode"], "require")
        self.assertEqual(url.drivername, "postgresql+psycopg")

    def test_browser_mode_counts_as_locked_down(self):
        Settings(app_env="production", auth_mode="browser", sandbox_backend="docker",
                 frontend_origins=["https://skillforge.example"], postgres_password="a-very-long-password-123",
                 _env_file=None)
        with self.assertRaises(ValueError):
            Settings(app_env="production", auth_mode="off", sandbox_backend="docker",
                     frontend_origins=["https://skillforge.example"],
                     postgres_password="a-very-long-password-123", _env_file=None)
