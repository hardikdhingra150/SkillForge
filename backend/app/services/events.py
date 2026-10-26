from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database.models import Execution, ExecutionEvent


def append_event(
    db: Session,
    execution_id: UUID,
    *,
    event_key: str,
    stage: str,
    event_type: str,
    message: str,
    payload: dict[str, Any] | None = None,
) -> int:
    next_sequence = db.execute(
        update(Execution)
        .where(Execution.id == execution_id)
        .values(
            next_event_sequence=(
                Execution.next_event_sequence + 1
            )
        )
        .returning(Execution.next_event_sequence)
    ).scalar_one()

    sequence = next_sequence - 1

    db.add(
        ExecutionEvent(
            execution_id=execution_id,
            sequence=sequence,
            event_key=event_key,
            stage=stage,
            event_type=event_type,
            message=message,
            payload_json=payload or {},
        )
    )

    return sequence