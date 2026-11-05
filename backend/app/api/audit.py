"""Read the audit trail: who promoted, retired, restored, imported, retried or rejected what, and why."""

import logging
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, DEV_WORKSPACE_ID
from app.database.audit_models import ACTIONS, AuditEvent
from app.security import require_access

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1", tags=["Audit"], dependencies=[Depends(require_access)])


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor: str
    action: str
    target: str
    reason: str
    details: dict[str, Any] = Field(validation_alias="details_json")
    created_at: datetime


@router.get("/audit", response_model=list[AuditEventOut])
def audit_trail(
    db: DB,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    action: Annotated[str | None, Query(max_length=40)] = None,
    target: Annotated[str | None, Query(max_length=160)] = None,
):
    """Newest first. Filter by action (e.g. skill.retired) or by an exact target (e.g. slugify@1.0.0)."""
    if action is not None and action not in ACTIONS:
        raise HTTPException(422, f"Unknown action. Use one of: {', '.join(ACTIONS)}.")
    query = select(AuditEvent).where(AuditEvent.workspace_id == DEV_WORKSPACE_ID)
    if action:
        query = query.where(AuditEvent.action == action)
    if target:
        query = query.where(AuditEvent.target == target)
    try:
        rows = db.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit)).all()
    except SQLAlchemyError as error:
        logger.error("Audit query failed: %s", getattr(error, "orig", error))
        raise HTTPException(503, "The audit trail is unavailable. Retry shortly.") from None
    return [AuditEventOut.model_validate(row) for row in rows]
