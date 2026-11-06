"""Workspace metrics from recorded runs: Workbench executions plus chat replies that used a skill."""

import logging
from dataclasses import dataclass

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB
from app.database.chat_models import ChatMessage, Conversation
from app.database.models import Execution, ExecutionEvent, Task
from app.database.skill_models import SkillVersion
from app.security import WorkspaceId, require_access
from app.services.skill_registry import visible_to

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1", tags=["Metrics"], dependencies=[Depends(require_access)])

FINISHED = {"succeeded", "failed", "waiting_approval"}
SKILL_EVENTS = {"reused", "created", "repaired"}


@dataclass(frozen=True)
class Run:
    ok: bool
    seconds: float | None
    events: tuple[str, ...]   # one per skill used: reused / created / repaired


def workbench_run(status, result, seconds):
    skill = (result or {}).get("skill") or {}
    event = "repaired" if skill.get("repaired_from") else "reused"
    return Run(status == "succeeded", seconds, (event,) if status == "succeeded" else ())


def chat_run(status, skill, seconds):
    """None for replies that used no skill (direct answers, clarifying questions)."""
    skill = skill or {}
    steps = skill.get("steps") if skill.get("event") == "pipeline" else [skill]
    events = tuple(step.get("event") for step in steps or [] if step.get("event") in SKILL_EVENTS)
    if status == "failed":
        return Run(False, seconds, ())
    return Run(True, seconds, events) if events else None


def summarize(runs: list[Run], skills: int, repaired_versions: int) -> dict:
    timed = [run.seconds for run in runs if run.ok and run.seconds is not None]
    events = [event for run in runs for event in run.events]
    return {
        "skills": skills,
        "runs": len(runs),
        "succeeded": sum(run.ok for run in runs),
        "success_rate": round(100 * sum(run.ok for run in runs) / len(runs), 1) if runs else None,
        "repairs": repaired_versions,
        "reuses": events.count("reused"),
        "created": events.count("created"),
        "average_seconds": round(sum(timed) / len(timed), 1) if timed else None,
    }


@router.get("/metrics/summary")
def metrics_summary(db: DB, workspace_id: WorkspaceId):
    try:
        skills = db.scalar(select(func.count(func.distinct(SkillVersion.skill_id)))
                           .where(visible_to(workspace_id), SkillVersion.status == "validated"))
        repaired = db.scalar(select(func.count()).select_from(SkillVersion)
                             .where(visible_to(workspace_id), SkillVersion.origin == "repaired"))
        # Time the skill run only (from the worker's first run event), not the wait for the user's CSV.
        run_started = (
            select(ExecutionEvent.execution_id, func.min(ExecutionEvent.created_at).label("at"))
            .where(ExecutionEvent.event_key.like("run.%"))
            .group_by(ExecutionEvent.execution_id).subquery()
        )
        executions = db.execute(
            select(Execution.status, Execution.result_json,
                   func.extract("epoch", Execution.finished_at - run_started.c.at))
            .join(Task, Task.id == Execution.task_id)
            .outerjoin(run_started, run_started.c.execution_id == Execution.id)
            .where(Task.workspace_id == workspace_id, Execution.status.in_(FINISHED))
        ).all()
        replies = db.execute(
            select(ChatMessage.status, ChatMessage.skill_json,
                   func.extract("epoch", ChatMessage.updated_at - ChatMessage.created_at))
            .join(Conversation, Conversation.id == ChatMessage.conversation_id)
            .where(Conversation.workspace_id == workspace_id, ChatMessage.role == "assistant",
                   ChatMessage.status.in_(("done", "failed")))
        ).all()
    except SQLAlchemyError as error:
        logger.error("Metrics query failed: %s", getattr(error, "orig", error))
        raise HTTPException(503, "Metrics are unavailable. Retry shortly.") from None

    seconds = lambda value: float(value) if value is not None else None  # noqa: E731
    runs = [workbench_run(status, result, seconds(elapsed)) for status, result, elapsed in executions]
    runs += [run for status, skill, elapsed in replies if (run := chat_run(status, skill, seconds(elapsed)))]
    return summarize(runs, skills or 0, repaired or 0)

