from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    pass


class Workspace(Base):
    __tablename__ = "workspaces"

    id = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    name = mapped_column(String(120), nullable=False)
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Task(Base):
    __tablename__ = "tasks"

    id = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    workspace_id = mapped_column(
        Uuid,
        ForeignKey("workspaces.id"),
        nullable=False,
        index=True,
    )
    requirement = mapped_column(Text, nullable=False)

    # Structured interpretation of the user's request.
    requirements_json = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(requirement)) > 0",
            name="ck_tasks_requirement_not_empty",
        ),
    )


class Execution(Base):
    __tablename__ = "executions"

    id = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("uuidv7()"),
    )
    task_id = mapped_column(
        Uuid,
        ForeignKey("tasks.id"),
        nullable=False,
        index=True,
    )
    status = mapped_column(
        String(32),
        nullable=False,
        server_default="queued",
    )
    current_stage = mapped_column(
        String(64),
        nullable=False,
        server_default="admission",
    )

    # Snapshot of the approved execution plan.
    plan_json = mapped_column(JSONB, nullable=True)
    result_json = mapped_column(JSONB, nullable=True)

    # The backend allocates event numbers transactionally.
    next_event_sequence = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("1"),
    )
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    started_at = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            "'queued', 'running', 'waiting_input', "
            "'waiting_approval', 'cancel_requested', "
            "'succeeded', 'failed', 'cancelled', 'expired'"
            ")",
            name="ck_executions_status",
        ),
        CheckConstraint(
            "next_event_sequence > 0",
            name="ck_executions_next_sequence",
        ),
        Index(
            "ix_executions_status_created_at",
            "status",
            "created_at",
        ),
    )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    execution_id = mapped_column(
        Uuid,
        ForeignKey("executions.id"),
        primary_key=True,
    )
    sequence = mapped_column(
        BigInteger,
        primary_key=True,
    )

    # Stable identifier to prevent duplicate event writes.
    event_key = mapped_column(String(128), nullable=False)

    stage = mapped_column(String(64), nullable=False)
    event_type = mapped_column(String(64), nullable=False)
    message = mapped_column(Text, nullable=False)

    # Safe details for the UI: tool name, version,
    # timing, validation evidence, artifact IDs, etc.
    payload_json = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "sequence > 0",
            name="ck_execution_events_sequence",
        ),
        UniqueConstraint(
            "execution_id",
            "event_key",
            name="uq_execution_events_event_key",
        ),
    )