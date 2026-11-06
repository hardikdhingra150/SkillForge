"""Pair a visitor's computer and relay work to it (see services/bridge.py).

The Studio uses the first three routes with the browser's own access. The program on the visitor's computer uses
the /connector/hello, /connector/next and /connector/jobs routes with its sfc_ token instead.
"""

import asyncio
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete

from app.api.tasks import DB
from app.database.connector_models import Connector
from app.database.session import SessionLocal
from app.security import WorkspaceId, is_visitor, require_access
from app.services import bridge

CLIENT = Path(__file__).resolve().parents[1] / "connector_client.py"

studio = APIRouter(prefix="/api/v1", tags=["Connector"], dependencies=[Depends(require_access)])
device = APIRouter(prefix="/api/v1", tags=["Connector"])


def api_base(request: Request) -> str:
    return str(request.base_url).rstrip("/") + "/api/v1"


def commands(request: Request, token: str) -> dict:
    base = api_base(request)
    return {
        "mac_linux": f"curl -fsSL {base}/connector.py -o skillforge-connect.py && "
                     f"python3 skillforge-connect.py --api {base} {token}",
        "windows": f"iwr {base}/connector.py -OutFile skillforge-connect.py; "
                   f"python skillforge-connect.py --api {base} {token}",
    }


def state(workspace_id) -> dict:
    return {"connected": bridge.relay.online(workspace_id), "models": bridge.relay.connected(workspace_id)}


@studio.get("/connector")
def connector_status(workspace_id: WorkspaceId):
    return state(workspace_id)


@studio.post("/connector", status_code=201)
def pair_computer(request: Request, workspace_id: WorkspaceId, db: DB):
    """A new token for this workspace's computer (any earlier one stops working). Shown once."""
    if not is_visitor(request):
        raise HTTPException(409, "You're the site owner: the server's own Claude and Codex logins serve you.")
    token = bridge.new_token()
    with db.begin():
        db.execute(delete(Connector).where(Connector.workspace_id == workspace_id))
        db.add(Connector(token_hash=bridge.token_hash(token), workspace_id=workspace_id))
    bridge.relay.forget(workspace_id)
    return {"token": token, "commands": commands(request, token), **state(workspace_id)}


@studio.delete("/connector", status_code=204)
def unpair_computer(workspace_id: WorkspaceId, db: DB):
    with db.begin():
        db.execute(delete(Connector).where(Connector.workspace_id == workspace_id))
    bridge.relay.forget(workspace_id)
    return Response(status_code=204)


@device.get("/connector.py", include_in_schema=False)
def connector_program():
    """The program visitors run on their computer (standard-library Python, nothing to install)."""
    return PlainTextResponse(CLIENT.read_text(), media_type="text/x-python")


# ---------- the program on the visitor's computer ----------

KNOWN: dict = {}  # token hash -> workspace id (a cache; the database is the truth)


def lookup(token_hash: str):
    with SessionLocal() as db:
        found = db.get(Connector, token_hash)
        return found.workspace_id if found else None


async def device_workspace(authorization: str | None):
    scheme, _, token = (authorization or "").partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token.startswith(bridge.PREFIX):
        raise HTTPException(401, {"code": "CONNECTOR_TOKEN_NEEDED", "message": "Pass the connector token."})
    digest = bridge.token_hash(token)
    workspace_id = await run_in_threadpool(lookup, digest)
    if workspace_id is None:
        KNOWN.pop(digest, None)
        raise HTTPException(401, {"code": "CONNECTOR_REVOKED",
                                  "message": "This connector was replaced or disconnected. Pair again in the Studio."})
    KNOWN[digest] = workspace_id
    return workspace_id


class Offer(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(max_length=20)
    available: bool
    detail: str = Field(default="", max_length=500)
    models: list[str] = Field(default_factory=list, max_length=20)
    default_model: str | None = Field(default=None, max_length=80)


class Hello(BaseModel):
    offers: list[Offer] = Field(max_length=4)


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str | None = Field(default=None, max_length=bridge.MAX_REPLY)
    error: str | None = Field(default=None, max_length=2000)


@device.post("/connector/hello")
async def connector_hello(body: Hello, authorization: Annotated[str | None, Header()] = None):
    workspace_id = await device_workspace(authorization)
    bridge.relay.hello(workspace_id, [offer.model_dump() for offer in body.offers])
    return state(workspace_id)


@device.get("/connector/next")
async def next_job(authorization: Annotated[str | None, Header()] = None,
                   wait: Annotated[float, Query(ge=0, le=25)] = 20) -> Any:
    """Long poll: a job as soon as there is one, else 204 after `wait` seconds."""
    workspace_id = await device_workspace(authorization)
    if bridge.relay.needs_hello(workspace_id):
        raise HTTPException(428, {"code": "SAY_HELLO", "message": "Send /connector/hello first."})
    deadline = asyncio.get_running_loop().time() + wait
    while True:
        job = bridge.relay.take(workspace_id)
        if job is not None:
            return job.public()
        if asyncio.get_running_loop().time() >= deadline:
            return Response(status_code=204)
        await asyncio.sleep(0.4)


@device.post("/connector/jobs/{job_id}", status_code=204)
async def job_result(job_id: str, body: Result, authorization: Annotated[str | None, Header()] = None):
    workspace_id = await device_workspace(authorization)
    if not bridge.relay.finish(workspace_id, job_id, text=body.text, error=body.error):
        raise HTTPException(404, "No such job, or it already finished.")
    return Response(status_code=204)
