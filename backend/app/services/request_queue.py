"""Short transactional queue review. Do not add file or model calls here.

The model-assisted review is split around the model call: claim_review() and finish_review() are short
transactions, and review_requested() runs the keyword rules, then a model, with no transaction open.
"""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Execution, Task
from app.services.events import append_event
from app.services.requirement_review import full_text, review_requirement, review_with_model

logger = logging.getLogger("skillforge.worker")
STALE_CLAIM = timedelta(minutes=10)

DEV_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


def queued_execution_statement(workspace_id: UUID | None):
    """The oldest request waiting for review, in one workspace or (None) across all of them."""
    statement = (
        select(Execution)
        .join(Task, Task.id == Execution.task_id)
        .where(
            Execution.status == "queued",
            Execution.current_stage == "admission",
        )
        .order_by(Execution.created_at, Execution.id)
        .limit(1)
        .with_for_update(of=Execution, skip_locked=True)
    )
    return statement if workspace_id is None else statement.where(Task.workspace_id == workspace_id)


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
    execution.started_at = execution.started_at or datetime.now(UTC)
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


def _prefix(task) -> str:
    rounds = (task.requirements_json or {}).get("review_round", 1)
    return "review.v1" if rounds == 1 else f"review.v1.round{rounds}"


def claim_review(db: Session, *, workspace_id: UUID | None = None):
    """Claim one queued request (or one whose review was abandoned by a crashed worker)."""
    execution = db.scalars(queued_execution_statement(workspace_id)).first()
    if execution is None:
        execution = db.scalars(
            select(Execution).join(Task, Task.id == Execution.task_id)
            .where(Execution.status == "running", Execution.current_stage == "requirement_review",
                   Execution.started_at < datetime.now(UTC) - STALE_CLAIM,
                   *([Task.workspace_id == workspace_id] if workspace_id is not None else []))
            .order_by(Execution.created_at).limit(1).with_for_update(of=Execution, skip_locked=True)
        ).first()
        if execution is None:
            return None
    task = db.get(Task, execution.task_id)
    execution.status, execution.current_stage = "running", "requirement_review"
    execution.started_at = datetime.now(UTC)
    db.flush()
    append_event(db, execution.id, event_key=f"{_prefix(task)}.execution_started", stage="requirement_review",
                 event_type="execution_started", message="A worker started reviewing this request.",
                 payload={"worker": "requirement_review_v2"})
    return {"execution_id": execution.id, "requirement": task.requirement, "workspace_id": task.workspace_id,
            "clarifications": list((task.requirements_json or {}).get("clarifications", []))}


def review_requested(claim, provider=None, model=None):
    """Keyword rules first (fast, exact); then a model for anything they do not recognize. No transaction here."""
    keyword = review_requirement(full_text(claim["requirement"], claim["clarifications"]))
    if keyword.candidate_workflow or provider is None:
        return keyword
    try:
        return review_with_model(claim["requirement"], claim["clarifications"], provider, model)
    except Exception as error:  # any model failure falls back to the rules
        logger.warning("Model review failed, using keyword rules: %s", error)
        return keyword


def finish_review(db: Session, execution_id: UUID, review) -> UUID | None:
    execution = db.scalars(select(Execution).where(Execution.id == execution_id).with_for_update()).first()
    if execution is None or execution.status != "running" or execution.current_stage != "requirement_review":
        return None  # someone else moved it on
    task = db.get(Task, execution.task_id)
    prefix = _prefix(task)
    task.requirements_json = {**(task.requirements_json or {}), "review": review.payload()}
    append_event(db, execution.id, event_key=f"{prefix}.requirements_checked", stage="requirement_review",
                 event_type="requirements_checked", message=review.summary, payload=review.payload())
    execution.status, execution.current_stage = "waiting_input", "awaiting_input"
    append_event(db, execution.id, event_key=f"{prefix}.input_required", stage="awaiting_input",
                 event_type="input_required", message=review.input_message,
                 payload={"next_action": review.next_action, "required_inputs": list(review.required_inputs),
                          "question": review.question, "method": review.method})
    db.flush()
    return execution.id
