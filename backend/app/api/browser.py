"""Public endpoints the app calls before it has a workspace: which mode the server runs in, and (in browser
mode) a new private workspace for this browser."""

from fastapi import APIRouter, HTTPException, Request

from app.api.tasks import DB
from app.config import settings
from app.rate_limit import limiter
from app.services import browser_workspaces

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace"])

# New workspaces per client address per minute: room for an office behind one address, not for a script.
NEW_WORKSPACES_PER_MINUTE = 30


@router.get("/config")
def workspace_config():
    return {"mode": settings.auth_mode}


@router.post("/browser", status_code=201)
def new_browser_workspace(request: Request, db: DB):
    if settings.auth_mode != "browser":
        raise HTTPException(404, "This server uses one shared workspace (AUTH_MODE=off).")
    client = request.client.host if request.client else "unknown"
    wait = limiter.check(("new-workspace", client), NEW_WORKSPACES_PER_MINUTE)
    if wait:
        raise HTTPException(429, "Too many new workspaces from this address. Try again in a minute.",
                            headers={"Retry-After": str(int(wait) + 1)})
    with db.begin():
        key = browser_workspaces.create(db)
    return {"key": key}
