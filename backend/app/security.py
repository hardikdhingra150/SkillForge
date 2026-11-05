"""API access: a single bearer token (API_TOKEN) guards every /api/v1 route except the health checks.

With no token configured, the API stays open in development (local use) and closed in production.
"""

import hmac
import logging
import re
from typing import Annotated

from fastapi import Header, HTTPException, Query, Request

from app.config import settings

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
    """Who made this request, for the audit trail: the token holder, or the local developer."""
    return "api-token" if getattr(request.state, "authenticated", False) else "local-dev"


def require_access(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Query(include_in_schema=False)] = None,
):
    expected = settings.api_token.get_secret_value() if settings.api_token else None
    if expected is None:
        if settings.app_env != "development":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "API_TOKEN_REQUIRED",
                    "message": "Set API_TOKEN before enabling the API in production.",
                },
            )
        return
    token = presented_token(request, authorization, access_token)
    if token is None or not hmac.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "This SkillForge API needs a valid access token."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.authenticated = True


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
