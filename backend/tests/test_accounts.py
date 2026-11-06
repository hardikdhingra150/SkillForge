import unittest
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.security import LOCAL_WORKSPACE_ID, WorkspaceId, require_access, require_operator
from app.services.accounts import check_new_password, check_password, hash_password, normalize_email

router = APIRouter(prefix="/api/v1", dependencies=[Depends(require_access)])


@router.get("/whoami")
def whoami(workspace_id: WorkspaceId):
    return {"workspace": str(workspace_id)}


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def accounts(token=None):
    return mock.patch.multiple("app.security.settings", auth_mode="accounts", app_env="development",
                               api_token=SecretStr(token) if token else None)


class PasswordTests(unittest.TestCase):
    def test_hash_round_trip_and_salting(self):
        first, second = hash_password("correct horse battery"), hash_password("correct horse battery")
        self.assertNotEqual(first, second)
        self.assertTrue(check_password("correct horse battery", first))
        self.assertFalse(check_password("correct horse batterz", first))
        self.assertFalse(check_password("x", "not-a-hash"))

    def test_rules(self):
        for password in ("short", "aaaaaaaaaaaa", "ana@example.com"):
            with self.subTest(password=password):
                with self.assertRaises(ValueError):
                    check_new_password(password, "ana@example.com")
        check_new_password("a-much-better-one", "ana@example.com")

    def test_emails(self):
        self.assertEqual(normalize_email("  Ana@Example.COM "), "ana@example.com")
        for email in ("ana", "ana@", "@x.io", "a b@x.io"):
            with self.subTest(email=email):
                with self.assertRaises(ValueError):
                    normalize_email(email)


class AccountsAccessTests(unittest.TestCase):
    def test_off_mode_uses_the_local_workspace(self):
        with mock.patch.multiple("app.security.settings", auth_mode="off", api_token=None, app_env="development"):
            self.assertEqual(client.get("/api/v1/whoami").json(), {"workspace": str(LOCAL_WORKSPACE_ID)})

    def test_accounts_mode_needs_a_sign_in(self):
        with accounts():
            response = client.get("/api/v1/whoami")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"]["code"], "SIGN_IN_REQUIRED")

    def test_a_session_selects_its_owners_workspace(self):
        workspace = uuid4()
        user = SimpleNamespace(workspace_id=workspace, email="ana@example.com")
        with accounts(), mock.patch("app.services.accounts.session_user", return_value=user), \
                mock.patch("app.database.session.SessionLocal"):
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer sfs_abc"})
        self.assertEqual(response.json(), {"workspace": str(workspace)})

    def test_expired_session(self):
        with accounts(), mock.patch("app.services.accounts.session_user", return_value=None), \
                mock.patch("app.database.session.SessionLocal"):
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer sfs_old"})
        self.assertEqual(response.json()["detail"]["code"], "SESSION_EXPIRED")

    def test_operator_token_still_works(self):
        with accounts("o" * 40):
            response = client.get("/api/v1/whoami", headers={"Authorization": "Bearer " + "o" * 40})
        self.assertEqual(response.json(), {"workspace": str(LOCAL_WORKSPACE_ID)})

    def test_signed_in_people_cannot_change_the_shared_library(self):
        signed_in = SimpleNamespace(state=SimpleNamespace(user_email="ana@example.com"))
        with mock.patch.multiple("app.security.settings", auth_mode="accounts"):
            with self.assertRaises(Exception) as caught:
                require_operator(signed_in)
        self.assertEqual(caught.exception.status_code, 403)


class ProductionSettingsTests(unittest.TestCase):
    def test_accounts_mode_counts_as_locked_down(self):
        Settings(app_env="production", auth_mode="accounts", sandbox_backend="docker",
                 frontend_origins=["https://skillforge.example"], postgres_password="a-very-long-password-123",
                 _env_file=None)
        with self.assertRaises(ValueError):
            Settings(app_env="production", sandbox_backend="docker", frontend_origins=["https://skillforge.example"],
                     postgres_password="a-very-long-password-123", _env_file=None)
