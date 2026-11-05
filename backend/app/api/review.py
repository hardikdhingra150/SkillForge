"""Human review: runs whose repair budget ran out, and manual control over skill versions."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, DEV_WORKSPACE_ID
from app.database.models import Execution, Task
from app.database.skill_models import SkillVersion
from app.security import require_access
from app.services.events import append_event
from app.services.skill_registry import SkillIntegrityError, verify

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1", tags=["Review"], dependencies=[Depends(require_access)])
MAX_BUDGET = 5


class RetryIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    extra_budget: int = Field(default=2, ge=1, le=MAX_BUDGET)


class RejectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="Rejected during review.", min_length=1, max_length=500)


def unavailable(error):
    logger.error("Review storage failed: %s", getattr(error, "orig", error))
    return HTTPException(503, "Review storage is unavailable. Retry shortly.")


def locked_run(db, execution_id):
    execution = db.scalars(select(Execution).where(Execution.id == execution_id).with_for_update()).first()
    task = db.get(Task, execution.task_id) if execution else None
    if execution is None or task.workspace_id != DEV_WORKSPACE_ID:
        raise HTTPException(404, "Run not found.")
    if execution.status != "waiting_approval":
        raise HTTPException(409, f"This run is {execution.status}, not waiting for review.")
    return execution, task


@router.get("/review")
def review_queue(db: DB):
    try:
        rows = db.execute(
            select(Execution, Task).join(Task, Task.id == Execution.task_id)
            .where(Execution.status == "waiting_approval", Task.workspace_id == DEV_WORKSPACE_ID)
            .order_by(Execution.created_at.desc()).limit(100)
        ).all()
    except SQLAlchemyError as error:
        raise unavailable(error) from None
    runs = []
    for execution, task in rows:
        error = (execution.result_json or {}).get("error", {})
        runs.append({
            "execution_id": str(execution.id), "requirement": task.requirement, "stage": execution.current_stage,
            "skill": (execution.result_json or {}).get("skill"), "failure": error.get("failure") or {"message": error.get("message")},
            "attempts": error.get("attempts", []), "repair_budget": (task.requirements_json or {}).get("repair_budget"),
            "created_at": execution.created_at.isoformat(), "finished_at": execution.finished_at.isoformat() if execution.finished_at else None,
        })
    return {"runs": runs}


@router.post("/executions/{execution_id}/review/retry")
def retry_run(execution_id: UUID, body: RetryIn, db: DB):
    """Queue the run again with a larger repair budget."""
    try:
        with db.begin():
            execution, task = locked_run(db, execution_id)
            meta = dict(task.requirements_json or {})
            attempt = meta.get("run_attempt", 1) + 1
            budget = min(MAX_BUDGET, (meta.get("repair_budget") or 2) + body.extra_budget)
            task.requirements_json = {**meta, "run_attempt": attempt, "repair_budget": budget}
            execution.status, execution.current_stage = "queued", "skill_discovery"
            execution.result_json, execution.finished_at = None, None
            append_event(db, execution.id, event_key=f"review.retry.{attempt}", stage="skill_discovery",
                         event_type="review_retried", message=f"A reviewer queued this run again with a repair budget of {budget}.",
                         payload={"repair_budget": budget, "attempt": attempt})
        return {"execution_id": str(execution_id), "status": "queued", "repair_budget": budget}
    except SQLAlchemyError as error:
        raise unavailable(error) from None


@router.post("/executions/{execution_id}/review/reject")
def reject_run(execution_id: UUID, body: RejectIn, db: DB):
    try:
        with db.begin():
            execution, task = locked_run(db, execution_id)
            execution.status, execution.current_stage = "failed", "failed"
            execution.finished_at = datetime.now(UTC)
            execution.result_json = {**(execution.result_json or {}), "review": {"decision": "rejected", "reason": body.reason}}
            append_event(db, execution.id, event_key=f"review.reject.{task.requirements_json.get('run_attempt', 1)}",
                         stage="failed", event_type="review_rejected", message=f"A reviewer rejected this run: {body.reason}",
                         payload={"reason": body.reason})
        return {"execution_id": str(execution_id), "status": "failed"}
    except SQLAlchemyError as error:
        raise unavailable(error) from None


def set_status(db, skill_id, version, status, note):
    skill = db.scalars(select(SkillVersion).where(SkillVersion.skill_id == skill_id, SkillVersion.version == version)
                       .with_for_update()).first()
    if skill is None:
        raise HTTPException(404, "Skill version not found.")
    if status == "validated":
        try:
            verify(skill)  # source, contract and evidence must still match before it can run again
        except SkillIntegrityError as error:
            raise HTTPException(409, f"Cannot restore: {error}") from None
    history = list((skill.change_json or {}).get("status_history", []))
    history.append({"from": skill.status, "to": status, "note": note, "at": datetime.now(UTC).isoformat()})
    skill.change_json = {**(skill.change_json or {}), "status_history": history}
    skill.status = status
    return {"skill_id": skill_id, "version": version, "status": status}


@router.post("/skills/{skill_id}/{version}/retire")
def retire_version(skill_id: str, version: str, db: DB):
    """Stop using a version. The previous validated version is selected again (a rollback)."""
    try:
        with db.begin():
            return set_status(db, skill_id, version, "retired", "Retired by a reviewer.")
    except SQLAlchemyError as error:
        raise unavailable(error) from None


@router.post("/skills/{skill_id}/{version}/restore")
def restore_version(skill_id: str, version: str, db: DB):
    """Put a retired version back into use, after re-checking its integrity."""
    try:
        with db.begin():
            return set_status(db, skill_id, version, "validated", "Restored by a reviewer.")
    except SQLAlchemyError as error:
        raise unavailable(error) from None
