import json
import logging
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, require_development
from app.database.skill_models import SkillVersion
from app.sandbox import PolicyViolation
from app.services.skill_bundle import BundleError, export_bundle, import_bundle

logger = logging.getLogger("uvicorn.error")
router = APIRouter(
    prefix="/api/v1", tags=["Skill registry"],
    dependencies=[Depends(require_development)],
)


class SkillVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    version: str
    capability: str
    status: str
    implementation_hash: str
    validation: dict[str, Any] = Field(validation_alias="validation_json")
    origin: str
    parent_version: str | None
    contract: dict[str, Any] | None = Field(validation_alias="contract_json")
    change: dict[str, Any] | None = Field(validation_alias="change_json")
    source_code: str | None
    created_at: datetime


class SkillPage(BaseModel):
    items: list[SkillVersionOut]
    has_more: bool
    next_after_skill_id: str | None
    next_after_version: str | None


@router.get("/skills", response_model=SkillPage)
def list_skills(
    db: DB,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    after_skill_id: Annotated[str | None, Query(min_length=1, max_length=80)] = None,
    after_version: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    status: Literal["draft", "validated", "retired"] | None = None,
    q: Annotated[str, Query(max_length=100)] = "",
):
    if (after_skill_id is None) != (after_version is None):
        raise HTTPException(400, "Both cursor fields must be supplied together.")

    statement = select(SkillVersion)
    if status is not None:
        statement = statement.where(SkillVersion.status == status)
    term = q.strip()
    if term:
        # Treat wildcard characters as literal search text.
        term = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        statement = statement.where(or_(
            SkillVersion.skill_id.ilike(pattern, escape="\\"),
            SkillVersion.capability.ilike(pattern, escape="\\"),
            SkillVersion.version.ilike(pattern, escape="\\"),
        ))
    if after_skill_id is not None:
        statement = statement.where(
            tuple_(SkillVersion.skill_id, SkillVersion.version)
            > (after_skill_id, after_version)
        )
    statement = statement.order_by(SkillVersion.skill_id, SkillVersion.version).limit(limit + 1)

    try:
        rows = db.scalars(statement).all()
        items = [SkillVersionOut.model_validate(row) for row in rows[:limit]]
    except SQLAlchemyError as error:
        original = getattr(error, "orig", error)
        diagnostic = getattr(original, "diag", None)
        reason = getattr(diagnostic, "message_primary", None) or str(original)
        logger.error("Skill registry read failed: %s", reason)
        raise HTTPException(503, "The skill registry is unavailable. Retry shortly.") from None

    has_more = len(rows) > limit
    return SkillPage(
        items=items,
        has_more=has_more,
        next_after_skill_id=items[-1].skill_id if has_more else None,
        next_after_version=items[-1].version if has_more else None,
    )


def registry_error(error):
    original = getattr(error, "orig", error)
    logger.error("Skill registry write failed: %s", getattr(getattr(original, "diag", None), "message_primary", None) or original)
    return HTTPException(503, "The skill registry is unavailable. Retry shortly.")


@router.get("/skills/{skill_id}/{version}/export")
def export_skill(skill_id: str, version: str, db: DB):
    """Download one version as a portable bundle (code, contract, evidence, lineage and fixtures)."""
    try:
        skill = db.get(SkillVersion, (skill_id, version))
        if skill is None:
            raise HTTPException(404, "Skill version not found.")
        bundle = export_bundle(db, skill)
    except BundleError as error:
        raise HTTPException(409, str(error)) from None
    except SQLAlchemyError as error:
        raise registry_error(error) from None
    filename = f"{skill_id}-v{version}.skillforge.json"
    return JSONResponse(bundle, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/skills/import", response_model=SkillVersionOut)
def import_skill(db: DB, bundle: dict[str, Any] = Body(...)):
    """Import a bundle. It is re-proven here: hash, sandbox policy, contract and every fixture must pass."""
    try:
        with db.begin():
            row, created = import_bundle(db, bundle)
            out = SkillVersionOut.model_validate(row)
    except (BundleError, PolicyViolation, ValueError) as error:
        raise HTTPException(422, f"Import rejected: {error}") from None
    except SQLAlchemyError as error:
        raise registry_error(error) from None
    return JSONResponse(out.model_dump(mode="json"), status_code=201 if created else 200)


@router.get("/mcp/config")
def mcp_config():
    """Exact commands to expose SkillForge's skills to coding agents over MCP, for this machine."""
    from pathlib import Path
    launcher = str(Path(__file__).resolve().parents[2] / "bin" / "skillforge-mcp")
    return {
        "launcher": launcher,
        "clients": [
            {"name": "Claude Code", "command": f"claude mcp add skillforge -- {launcher}"},
            {"name": "Codex", "command": f"codex mcp add skillforge -- {launcher}"},
            {"name": "Cursor (~/.cursor/mcp.json)",
             "command": json.dumps({"mcpServers": {"skillforge": {"command": launcher}}}, indent=2)},
        ],
        "notes": "Postgres must be running (make db). New and repaired skills appear as tools automatically.",
    }
