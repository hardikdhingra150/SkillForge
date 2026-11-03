import logging
import time
from collections.abc import Callable, Iterator
from typing import Annotated
from uuid import UUID, uuid5

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
    Response,
)
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database.models import (
    Execution,
    ExecutionEvent,
    Task,
    Workspace,
)
from app.database.session import SessionLocal, get_db
from app.schemas.process import (
    EventOut,
    EventPage,
    ExecutionOut,
    TaskCreate,
)
from app.services.events import append_event

logger = logging.getLogger("uvicorn.error")

DEV_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")

DB = Annotated[Session, Depends(get_db)]


def require_development():
    if settings.app_env != "development":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "LOCAL_API_DISABLED",
                "message": (
                    "Workspace authentication must be configured "
                    "before enabling these routes in production."
                ),
            },
        )


router = APIRouter(
    prefix="/api/v1",
    tags=["Tasks and process"],
    dependencies=[Depends(require_development)],
)


def log_database_error(error: SQLAlchemyError):
    original = getattr(error, "orig", error)
    diagnostic = getattr(original, "diag", None)

    reason = (
        getattr(diagnostic, "message_primary", None)
        or str(original)
        or "Unknown database error"
    )

    logger.error(
        "Task database operation failed: %s; "
        "SQLSTATE=%s; reason=%s",
        type(original).__name__,
        getattr(original, "sqlstate", None),
        reason,
    )

def lookup_execution(db: Session, execution_id: UUID):
    return db.execute(
        select(Execution, Task)
        .join(Task, Task.id == Execution.task_id)
        .where(
            Execution.id == execution_id,
            Task.workspace_id == DEV_WORKSPACE_ID,
        )
    ).first()


def execution_output(
    execution: Execution,
    task: Task,
) -> ExecutionOut:
    return ExecutionOut(
        task_id=task.id,
        execution_id=execution.id,
        requirement=task.requirement,
        status=execution.status,
        current_stage=execution.current_stage,
        created_at=execution.created_at,
        plan=execution.plan_json,
        result=execution.result_json,
    )


def replay_submission(
    row,
    body: TaskCreate,
    response: Response,
) -> ExecutionOut:
    execution, task = row

    if task.requirement != body.requirement:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": (
                    "This submission key was already used "
                    "for a different requirement."
                ),
            },
        )

    response.status_code = 200
    return execution_output(execution, task)


@router.post(
    "/tasks",
    response_model=ExecutionOut,
    status_code=202,
)
def create_task(
    body: TaskCreate,
    response: Response,
    idempotency_key: Annotated[
        UUID,
        Header(alias="Idempotency-Key"),
    ],
    db: DB,
):
    execution_id = uuid5(
        DEV_WORKSPACE_ID,
        str(idempotency_key),
    )

    try:
        with db.begin():
            db.execute(
                insert(Workspace)
                .values(
                    id=DEV_WORKSPACE_ID,
                    name="Local development",
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )

            existing = lookup_execution(db, execution_id)

            if existing is not None:
                return replay_submission(existing, body, response)

            task = Task(
                workspace_id=DEV_WORKSPACE_ID,
                requirement=body.requirement,
                requirements_json={},
            )
            db.add(task)
            db.flush()

            execution = Execution(
                id=execution_id,
                task_id=task.id,
                status="queued",
                current_stage="admission",
            )
            db.add(execution)
            db.flush()

            append_event(
                db,
                execution.id,
                event_key="admission.task_received",
                stage="admission",
                event_type="task_received",
                message="Your request has been saved.",
                payload={"task_id": str(task.id)},
            )

            append_event(
                db,
                execution.id,
                event_key="admission.execution_queued",
                stage="admission",
                event_type="execution_queued",
                message="Execution queued.",
                payload={"execution_id": str(execution.id)},
            )

            db.flush()
            output = execution_output(execution, task)

        return output

    except IntegrityError as error:
        db.rollback()

        # A concurrent request may have saved this submission.
        existing = lookup_execution(db, execution_id)

        if existing is not None:
            return replay_submission(existing, body, response)

        log_database_error(error)

        raise HTTPException(
            status_code=500,
            detail={
                "code": "TASK_SAVE_FAILED",
                "message": "The task could not be saved.",
            },
        ) from None

    except SQLAlchemyError as error:
        db.rollback()
        log_database_error(error)

        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_ERROR",
                "message": (
                    "The database operation failed. "
                    "Retry using the same submission key."
                ),
            },
        ) from None


@router.get(
    "/executions/{execution_id}",
    response_model=ExecutionOut,
)
def get_execution(execution_id: UUID, db: DB):
    row = lookup_execution(db, execution_id)

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found.",
        )

    execution, task = row
    return execution_output(execution, task)


@router.get(
    "/executions/{execution_id}/events",
    response_model=EventPage,
)
def get_events(
    execution_id: UUID,
    db: DB,
    after: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
):
    if lookup_execution(db, execution_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Execution not found.",
        )

    rows = db.scalars(
        select(ExecutionEvent)
        .where(
            ExecutionEvent.execution_id == execution_id,
            ExecutionEvent.sequence > after,
        )
        .order_by(ExecutionEvent.sequence)
        .limit(limit + 1)
    ).all()

    events = [
        EventOut.model_validate(row)
        for row in rows[:limit]
    ]

    return EventPage(
        events=events,
        next_after=events[-1].sequence if events else after,
        has_more=len(rows) > limit,
    )

# Short-lived streams: the browser reconnects, and a dev reload never waits on an open stream for long.
STREAM_MAX_SECONDS = 30
STREAM_POLL_SECONDS = 1.0
FINISHED = {"succeeded", "failed", "cancelled", "expired"}


def stream_frames(
    load: Callable[[int], tuple[ExecutionOut, list[EventOut]]],
    after: int = 0,
    *,
    sleep: Callable[[float], None] = time.sleep,
    max_seconds: float = STREAM_MAX_SECONDS,
    clock: Callable[[], float] = time.monotonic,
) -> Iterator[str]:
    """Server-sent event frames: the run when it changes, each new event once, then `done` when it finishes
    (or `reconnect` when the time limit ends first).

    The worker is a separate process, so this polls the database (cheap: one indexed read per second).
    """
    started, last, cursor = clock(), None, after
    while clock() - started < max_seconds:
        execution, events = load(cursor)
        for event in events:
            cursor = event.sequence
            yield f"id: {event.sequence}\nevent: event\ndata: {event.model_dump_json()}\n\n"
        payload = execution.model_dump_json()
        if payload != last:
            last = payload
            yield f"event: execution\ndata: {payload}\n\n"
        if execution.status in FINISHED:
            yield "event: done\ndata: {}\n\n"
            return
        yield ": keep-alive\n\n"
        sleep(STREAM_POLL_SECONDS)
    yield "event: reconnect\ndata: {}\n\n"


@router.get("/executions/{execution_id}/stream")
def stream_execution(
    execution_id: UUID,
    after: Annotated[int, Query(ge=0)] = 0,
):
    """Live updates for one run over server-sent events; the Process view falls back to polling."""
    with SessionLocal() as db:
        if lookup_execution(db, execution_id) is None:
            raise HTTPException(status_code=404, detail="Execution not found.")

    def load(cursor: int):
        with SessionLocal() as db:
            execution, task = lookup_execution(db, execution_id)
            rows = db.scalars(
                select(ExecutionEvent)
                .where(ExecutionEvent.execution_id == execution_id, ExecutionEvent.sequence > cursor)
                .order_by(ExecutionEvent.sequence)
                .limit(100)
            ).all()
            return (
                execution_output(execution, task),
                [EventOut.model_validate(row) for row in rows],
            )

    return StreamingResponse(
        stream_frames(load, after),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
