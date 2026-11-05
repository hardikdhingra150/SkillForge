from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from app.database.models import Base

ACTIONS = (
    "skill.promoted", "skill.retired", "skill.restored", "skill.imported",
    "run.retried", "run.rejected",
)


class AuditEvent(Base):
    """Who changed what the registry trusts, and why. Append-only."""

    __tablename__ = "audit_events"

    id = mapped_column(Uuid, primary_key=True, server_default=text("uuidv7()"))
    workspace_id = mapped_column(Uuid, ForeignKey("workspaces.id"), nullable=False, index=True)
    # "api-token", "local-dev", "worker" or "agent"
    actor = mapped_column(String(40), nullable=False)
    action = mapped_column(String(40), nullable=False)
    # e.g. "revenue_by_product@1.1.0" or an execution id
    target = mapped_column(String(160), nullable=False)
    reason = mapped_column(String(500), nullable=False)
    details_json = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    created_at = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    __table_args__ = (
        CheckConstraint("action IN ('" + "', '".join(ACTIONS) + "')", name="ck_audit_events_action"),
    )
