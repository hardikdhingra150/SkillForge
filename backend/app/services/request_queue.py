"""Short transactional queue review. Do not add file or model calls here."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Execution, Task
from app.services.events import append_event
from app.services.requirement_review import review_requirement

DEV_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


def queued_execution_statement(workspace_id: UUID):
    return (
        select(Execution)
        .join(Task, Task.id == Execution.task_id)
        .where(
            Execution.status == "queued",
            Execution.current_stage == "admission",
            Task.workspace_id == workspace_id,
        )
        .order_by(Execution.created_at, Execution.id)
        .limit(1)
        .with_for_update(of=Execution, skip_locked=True)
    )


def review_next(
    db: Session,
    *,
    workspace_id: UUID = DEV_WORKSPACE_ID,
) -> UUID | None:
    """Caller must commit/rollback the claim, review, status, and events together."""
    if not db.in_transaction():
        raise RuntimeError("Call review_next inside an explicit transaction.")

    execution = db.scalars(queued_execution_statement(workspace_id)).first()
    if execution is None:
        return None

    task = db.get(Task, execution.task_id)
    if task is None:
        raise RuntimeError("The queued execution has no task.")

    execution.status = "running"
    execution.current_stage = "requirement_review"
    execution.started_at = execution.started_at or datetime.now(timezone.utc)
    db.flush()

    append_event(
        db,
        execution.id,
        event_key="review.v1.execution_started",
        stage="requirement_review",
        event_type="execution_started",
        message="A worker started reviewing this request.",
        payload={"worker": "requirement_review_v1"},
    )

    review = review_requirement(task.requirement)
    task.requirements_json = {
        **(task.requirements_json or {}),
        "review": review.payload(),
    }

    append_event(
        db,
        execution.id,
        event_key="review.v1.requirements_checked",
        stage="requirement_review",
        event_type="requirements_checked",
        message=review.summary,
        payload=review.payload(),
    )

    execution.status = "waiting_input"
    execution.current_stage = "awaiting_input"

    append_event(
        db,
        execution.id,
        event_key="review.v1.input_required",
        stage="awaiting_input",
        event_type="input_required",
        message=review.input_message,
        payload={
            "next_action": review.next_action,
            "required_inputs": list(review.required_inputs),
        },
    )

    db.flush()
    return execution.id
