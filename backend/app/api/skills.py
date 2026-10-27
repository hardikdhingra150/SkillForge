import logging
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, require_development
from app.database.skill_models import SkillVersion

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
