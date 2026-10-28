import logging
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from pydantic import BaseModel
from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import (
    DB,
    DEV_WORKSPACE_ID,
    require_development,
)
from app.database.models import Execution, Task


logger = logging.getLogger("uvicorn.error")

router = APIRouter(
    prefix="/api/v1",
    tags=["Activity"],
    dependencies=[
        Depends(require_development)
    ],
)

RunStatus = Literal[
    "queued",
    "running",
    "waiting_input",
    "waiting_approval",
    "cancel_requested",
    "succeeded",
    "failed",
    "cancelled",
    "expired",
]


class RunSummary(BaseModel):
    execution_id: UUID
    task_id: UUID
    requirement_preview: str
    status: str
    current_stage: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class RunPage(BaseModel):
    items: list[RunSummary]
    has_more: bool
    next_before_created_at: datetime | None
    next_before_execution_id: UUID | None


def utc(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


@router.get(
    "/executions",
    response_model=RunPage,
)
def list_executions(
    db: DB,
    limit: Annotated[
        int,
        Query(ge=1, le=100),
    ] = 24,
    before_created_at: datetime | None = None,
    before_execution_id: UUID | None = None,
    status: RunStatus | None = None,
    q: Annotated[
        str,
        Query(max_length=100),
    ] = "",
):
    if (
        (before_created_at is None)
        != (before_execution_id is None)
    ):
        raise HTTPException(
            400,
            "Both cursor fields must "
            "be supplied together.",
        )

    if (
        before_created_at is not None
        and before_created_at.utcoffset()
        is None
    ):
        raise HTTPException(
            400,
            "The cursor timestamp must "
            "include its timezone.",
        )

    statement = (
        select(
            Execution.id.label(
                "execution_id"
            ),
            Task.id.label("task_id"),
            func.substr(
                Task.requirement,
                1,
                241,
            ).label(
                "requirement_preview"
            ),
            Execution.status,
            Execution.current_stage,
            Execution.created_at,
            Execution.started_at,
            Execution.finished_at,
        )
        .join(
            Task,
            Task.id == Execution.task_id,
        )
        .where(
            Task.workspace_id
            == DEV_WORKSPACE_ID
        )
    )

    if status is not None:
        statement = statement.where(
            Execution.status == status
        )

    term = q.strip()

    if term:
        term = (
            term
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        statement = statement.where(
            Task.requirement.ilike(
                f"%{term}%",
                escape="\\",
            )
        )

    if before_created_at is not None:
        statement = statement.where(
            tuple_(
                Execution.created_at,
                Execution.id,
            )
            < (
                utc(before_created_at),
                before_execution_id,
            )
        )

    statement = (
        statement
        .order_by(
            Execution.created_at.desc(),
            Execution.id.desc(),
        )
        .limit(limit + 1)
    )

    try:
        rows = (
            db.execute(statement)
            .mappings()
            .all()
        )

        items = []

        for row in rows[:limit]:
            value = dict(row)

            preview = value[
                "requirement_preview"
            ]

            value[
                "requirement_preview"
            ] = (
                preview[:240]
                + (
                    "…"
                    if len(preview) > 240
                    else ""
                )
            )

            for field in (
                "created_at",
                "started_at",
                "finished_at",
            ):
                value[field] = utc(
                    value[field]
                )

            items.append(
                RunSummary(**value)
            )

    except SQLAlchemyError as error:
        original = getattr(
            error,
            "orig",
            error,
        )

        diagnostic = getattr(
            original,
            "diag",
            None,
        )

        reason = (
            getattr(
                diagnostic,
                "message_primary",
                None,
            )
            or str(original)
        )

        logger.error(
            "Activity read failed: %s",
            reason,
        )

        raise HTTPException(
            503,
            "Task history is unavailable. "
            "Retry shortly.",
        ) from None

    has_more = len(rows) > limit

    return RunPage(
        items=items,
        has_more=has_more,
        next_before_created_at=(
            items[-1].created_at
            if has_more
            else None
        ),
        next_before_execution_id=(
            items[-1].execution_id
            if has_more
            else None
        ),
    )