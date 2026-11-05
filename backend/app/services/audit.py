"""The audit trail: every promotion, rollback, import and review decision, with who and why."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.audit_models import AuditEvent
from app.database.models import Workspace

DEV_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


def skill_target(skill_id: str, version: str) -> str:
    return f"{skill_id}@{version}"


def record(db: Session, *, actor: str, action: str, target: str, reason: str, details: dict | None = None,
           workspace_id=DEV_WORKSPACE_ID) -> AuditEvent:
    """Add an audit event to the caller's transaction, so it commits (or rolls back) with the change."""
    if workspace_id == DEV_WORKSPACE_ID and hasattr(db, "execute"):
        # A fresh database has no workspace row until the first task or chat; skills can change before that.
        db.execute(insert(Workspace).values(id=DEV_WORKSPACE_ID, name="Local development")
                   .on_conflict_do_nothing(index_elements=["id"]))
    event = AuditEvent(workspace_id=workspace_id, actor=actor[:40], action=action, target=target[:160],
                       reason=(reason or "No reason given.")[:500], details_json=details or {})
    db.add(event)
    return event
