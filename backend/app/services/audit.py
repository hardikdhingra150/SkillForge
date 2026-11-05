"""The audit trail: every promotion, rollback, import and review decision, with who and why."""

from sqlalchemy.orm import Session

from app.database.audit_models import AuditEvent

DEV_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def skill_target(skill_id: str, version: str) -> str:
    return f"{skill_id}@{version}"


def record(db: Session, *, actor: str, action: str, target: str, reason: str, details: dict | None = None,
           workspace_id=DEV_WORKSPACE_ID) -> AuditEvent:
    """Add an audit event to the caller's transaction, so it commits (or rolls back) with the change."""
    event = AuditEvent(workspace_id=workspace_id, actor=actor[:40], action=action, target=target[:160],
                       reason=(reason or "No reason given.")[:500], details_json=details or {})
    db.add(event)
    return event
