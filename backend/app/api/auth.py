"""Sign up, sign in and sign out (AUTH_MODE=accounts). /auth/config is public so the app knows what to show."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError

from app.api.tasks import DB
from app.config import settings
from app.database.account_models import User
from app.database.models import Workspace
from app.security import WorkspaceId, require_access
from app.services import accounts

router = APIRouter(prefix="/api/v1/auth", tags=["Accounts"])


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=200)
    name: str = Field(default="", max_length=120)


def person(user: User, workspace: Workspace | None = None):
    return {"email": user.email, "name": user.name, "workspace": workspace.name if workspace else None}


def accounts_only():
    if settings.auth_mode != "accounts":
        raise HTTPException(404, "Accounts are off. Set AUTH_MODE=accounts in backend/.env to use them.")


@router.get("/config")
def auth_config():
    return {"mode": settings.auth_mode, "allow_signup": settings.allow_signup}


@router.post("/signup", status_code=201, dependencies=[Depends(accounts_only)])
def signup(body: Credentials, db: DB):
    if not settings.allow_signup:
        raise HTTPException(403, "New accounts are closed on this server. Ask its owner to invite you.")
    try:
        with db.begin():
            user = accounts.create_user(db, body.email, body.password, body.name)
            token = accounts.start_session(db, user)
            workspace = db.get(Workspace, user.workspace_id)
            result = {"token": token, "user": person(user, workspace)}
        return result
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    except IntegrityError as error:
        if "users_email" in str(getattr(error, "orig", error)):
            raise HTTPException(409, "An account with this email already exists. Sign in instead.") from None
        raise


@router.post("/login", dependencies=[Depends(accounts_only)])
def login(body: Credentials, db: DB):
    with db.begin():
        user = accounts.authenticate(db, body.email, body.password)
        if user is None:
            raise HTTPException(401, {"code": "BAD_CREDENTIALS", "message": "That email and password don't match."})
        token = accounts.start_session(db, user)
        result = {"token": token, "user": person(user, db.get(Workspace, user.workspace_id))}
    return result


@router.post("/logout", status_code=204, dependencies=[Depends(accounts_only)])
def logout(db: DB, authorization: Annotated[str | None, Header()] = None):
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer" and token.startswith("sfs_"):
        with db.begin():
            accounts.end_session(db, token.strip())
    return Response(status_code=204)


@router.get("/me", dependencies=[Depends(require_access)])
def me(request: Request, workspace_id: WorkspaceId, db: DB):
    email = getattr(request.state, "user_email", None)
    workspace = db.get(Workspace, workspace_id)
    user = None
    if email:
        from sqlalchemy import select

        found = db.scalars(select(User).where(User.email == email)).first()
        user = person(found, workspace) if found else None
    return {"mode": settings.auth_mode, "user": user, "workspace": workspace.name if workspace else "Local workspace"}
