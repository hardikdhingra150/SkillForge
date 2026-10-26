from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

RequirementText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=5,
        max_length=10000,
    ),
]


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement: RequirementText


class ExecutionOut(BaseModel):
    task_id: UUID
    execution_id: UUID
    requirement: str
    status: str
    current_stage: str
    created_at: datetime
    plan: dict[str, Any] | None
    result: dict[str, Any] | None


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    execution_id: UUID
    sequence: int
    stage: str
    event_type: str
    message: str
    payload: dict[str, Any] = Field(
        validation_alias="payload_json"
    )
    created_at: datetime


class EventPage(BaseModel):
    events: list[EventOut]
    next_after: int
    has_more: bool