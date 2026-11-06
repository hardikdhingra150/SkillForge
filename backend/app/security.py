"""API access for every /api/v1 route except the health checks and sign-in.

AUTH_MODE=off: one shared local workspace. A single bearer token (API_TOKEN) guards it; with no token the API
stays open in development and closed in production.
AUTH_MODE=browser: no sign-in. Each browser gets its own private workspace and a random key (sfb_...) that selects
it. API_TOKEN, if set, still works for tools such as the MCP server and selects the shared local workspace.
"""

import hmac
import logging
import re
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Query, Request

from app.config import settings

LOCAL_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")

logger = logging.getLogger("uvicorn.error")

# EventSource cannot send headers, so live streams may pass the token as ?access_token=.
STREAM_SUFFIX = "/stream"


def presented_token(request: Request, authorization: str | None, access_token: str | None) -> str | None:
    if authorization:
        scheme, _, value = authorization.partition(" ")
        return value.strip() if scheme.lower() == "bearer" else None
    if access_token and request.url.path.endswith(STREAM_SUFFIX):
        return access_token
    return None


def actor(request: Request) -> str:
    """Who made this request, for the audit trail: a browser workspace, the token holder, or the local developer."""
    if getattr(request.state, "browser", False):
        return "browser"
    return "api-token" if getattr(request.state, "authenticated", False) else "local-dev"


def unauthorized(code: str, message: str):
    return HTTPException(status_code=401, detail={"code": code, "message": message},
                         headers={"WWW-Authenticate": "Bearer"})


def require_access(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query(include_in_schema=False)] = None,
) -> UUID:
    """Check the caller and return the workspace this request acts on."""
    expected = settings.api_token.get_secret_value() if settings.api_token else None
    request.state.workspace_id = LOCAL_WORKSPACE_ID
    if settings.auth_mode == "browser":
        token = presented_token(request, authorization, access_token)
        if token and token.startswith("sfb_"):
            from app.database.session import SessionLocal
            from app.services.browser_workspaces import workspace_for

            with SessionLocal() as db:
                workspace_id = workspace_for(db, token)
            if workspace_id is None:
                raise unauthorized("BROWSER_KEY_UNKNOWN", "This browser's workspace no longer exists.")
            request.state.workspace_id = workspace_id
            request.state.browser = True
            return workspace_id
        if expected and token and hmac.compare_digest(token.encode(), expected.encode()):
            request.state.authenticated = True
            return LOCAL_WORKSPACE_ID
        raise unauthorized("BROWSER_KEY_NEEDED", "Ask POST /api/v1/workspace/browser for this browser's workspace.")
    if expected is None:
        if settings.app_env != "development":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "API_TOKEN_REQUIRED",
                    "message": "Set API_TOKEN before enabling the API in production.",
                },
            )
        return LOCAL_WORKSPACE_ID
    token = presented_token(request, authorization, access_token)
    if token is None or not hmac.compare_digest(token.encode(), expected.encode()):
        raise unauthorized("UNAUTHORIZED", "This SkillForge API needs a valid access token.")
    request.state.authenticated = True
    return LOCAL_WORKSPACE_ID


def is_visitor(request: Request) -> bool:
    """A browser-mode visitor, as opposed to the owner (API_TOKEN) or the single user of AUTH_MODE=off."""
    return getattr(request.state, "browser", False)


def models_for(request: Request) -> list[str] | None:
    """The model providers this caller may use: every one for the owner, the public ones for a visitor."""
    return list(settings.public_providers) if is_visitor(request) else None


def models_for_workspace(workspace_id: UUID | None) -> list[str] | None:
    """The same rule for background work, which knows only the workspace: the owner's is the local one."""
    if settings.auth_mode == "browser" and workspace_id != LOCAL_WORKSPACE_ID:
        return list(settings.public_providers)
    return None


def require_operator(request: Request):
    """Changes to the shared skill library. In browser mode, only the operator's API_TOKEN may make them."""
    if getattr(request.state, "browser", False):
        raise HTTPException(403, "The skill library is shared by everyone on this server. Only its operator "
                                 "(with API_TOKEN) can retire, restore or import skills.")


# The workspace a request acts on. FastAPI caches require_access per request, so this adds no second check.
WorkspaceId = Annotated[UUID, Depends(require_access)]


class RedactTokens(logging.Filter):
    """Hide ?access_token= values in log lines (uvicorn's access log prints full URLs)."""

    PATTERN = re.compile(r"(access_token=)[^&\s\"']+")

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(self.PATTERN.sub(r"\1<redacted>", a) if isinstance(a, str) else a for a in record.args)
        if isinstance(record.msg, str):
            record.msg = self.PATTERN.sub(r"\1<redacted>", record.msg)
        return True


def redact_access_logs():
    for name in ("uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactTokens) for f in logger.filters):
            logger.addFilter(RedactTokens())
