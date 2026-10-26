import hashlib
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB, DEV_WORKSPACE_ID, require_development
from app.database.input_models import ExecutionCSVInput
from app.database.models import Execution, Task
from app.services.csv_inputs import MAX_BYTES, parse_csv, validate_mapping
from app.services.events import append_event

logger = logging.getLogger("uvicorn.error")
router = APIRouter(
    prefix="/api/v1", tags=["Task inputs"],
    dependencies=[Depends(require_development)],
)


class CSVInputOut(BaseModel):
    execution_id: UUID
    filename: str
    sha256: str
    version: int
    headers: list[str]
    row_count: int
    preview: list[list[str]]
    column_mapping: dict[str, str] | None
    confirmed: bool


class MappingConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    file_version: int = Field(ge=1)
    product_column: str = Field(min_length=1, max_length=120)
    revenue_column: str = Field(min_length=1, max_length=120)


def output(item):
    return CSVInputOut(
        execution_id=item.execution_id, filename=item.filename,
        sha256=item.sha256, version=item.version,
        headers=item.headers_json, row_count=item.row_count,
        preview=item.preview_json, column_mapping=item.mapping_json,
        confirmed=item.confirmed_at is not None,
    )


def execution_row(db, execution_id, *, lock=False):
    statement = select(Execution, Task).join(Task, Task.id == Execution.task_id).where(
        Execution.id == execution_id, Task.workspace_id == DEV_WORKSPACE_ID,
    )
    if lock:
        statement = statement.with_for_update(of=Execution)
    row = db.execute(statement).first()
    if row is None:
        raise HTTPException(404, "Task run not found.")
    return row


def database_error(error):
    original = getattr(error, "orig", error)
    diagnostic = getattr(original, "diag", None)
    reason = getattr(diagnostic, "message_primary", None) or str(original)
    logger.error("CSV input database operation failed: %s", reason)
    return HTTPException(503, "The input could not be saved or loaded. Retry the same action.")


@router.get("/executions/{execution_id}/input", response_model=CSVInputOut)
def get_input(execution_id: UUID, db: DB):
    try:
        execution_row(db, execution_id)
        item = db.get(ExecutionCSVInput, execution_id)
        if item is None:
            raise HTTPException(404, "No CSV has been uploaded for this task.")
        return output(item)
    except SQLAlchemyError as error:
        raise database_error(error) from None


@router.post("/executions/{execution_id}/input", response_model=CSVInputOut, status_code=201)
def upload_input(
    execution_id: UUID, db: DB, response: Response,
    file: Annotated[UploadFile, File()],
):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not filename.casefold().endswith(".csv"):
        raise HTTPException(422, "Choose a .csv file.")
    filename = "".join(char for char in filename if char.isprintable())[:200]
    content = file.file.read(MAX_BYTES + 1)
    try:
        headers, rows = parse_csv(content)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    digest = hashlib.sha256(content).hexdigest()

    try:
        with db.begin():
            execution, task = execution_row(db, execution_id, lock=True)
            review = (task.requirements_json or {}).get("review", {})
            if review.get("candidate_workflow") != "revenue_by_product":
                raise HTTPException(409, "This task needs clarification before accepting a sales CSV.")
            item = db.get(ExecutionCSVInput, execution_id)
            if item is not None and item.sha256 == digest:
                response.status_code = 200
                return output(item)
            if execution.status != "waiting_input" or execution.current_stage not in {"awaiting_input", "column_mapping"}:
                raise HTTPException(409, "This task is not accepting a new CSV. Start a new task to use different input.")
            if item is None:
                item = ExecutionCSVInput(execution_id=execution_id, version=1)
                db.add(item)
            else:
                item.version += 1
            item.filename = filename
            item.sha256 = digest
            item.size_bytes = len(content)
            item.content_bytes = content
            item.headers_json = headers
            item.preview_json = rows[:5]
            item.row_count = len(rows)
            item.mapping_json = None
            item.confirmed_at = None
            item.uploaded_at = datetime.now(timezone.utc)
            execution.current_stage = "column_mapping"
            append_event(
                db, execution_id, event_key=f"input.csv_uploaded.v{item.version}",
                stage="input_validation", event_type="csv_uploaded",
                message=f"Uploaded {filename}.",
                payload={"filename": filename, "sha256": digest, "size_bytes": len(content)},
            )
            append_event(
                db, execution_id, event_key=f"input.csv_inspected.v{item.version}",
                stage="column_mapping", event_type="csv_inspected",
                message=f"Read {len(rows)} data rows and {len(headers)} columns. Confirm the product and revenue columns.",
                payload={"headers": headers, "row_count": len(rows)},
            )
            db.flush()
            result = output(item)
        return result
    except SQLAlchemyError as error:
        raise database_error(error) from None


@router.post("/executions/{execution_id}/input/confirm", response_model=CSVInputOut)
def confirm_input(execution_id: UUID, body: MappingConfirm, db: DB):
    try:
        with db.begin():
            execution, task = execution_row(db, execution_id, lock=True)
            item = db.get(ExecutionCSVInput, execution_id)
            if item is None:
                raise HTTPException(409, "Upload a CSV before confirming columns.")
            if item.sha256 != body.file_sha256 or item.version != body.file_version:
                raise HTTPException(409, "The uploaded file changed. Refresh the page and confirm its current columns.")
            mapping = {"product": body.product_column, "revenue": body.revenue_column}
            if item.confirmed_at is not None:
                if item.mapping_json == mapping:
                    return output(item)
                raise HTTPException(409, "These columns are already confirmed. Start a new task to use a different mapping.")
            if execution.status != "waiting_input" or execution.current_stage != "column_mapping":
                raise HTTPException(409, "This task is not waiting for column confirmation.")
            try:
                headers, rows = parse_csv(item.content_bytes)
                validate_mapping(headers, rows, body.product_column, body.revenue_column)
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            item.mapping_json = mapping
            item.confirmed_at = datetime.now(timezone.utc)
            task.requirements_json = {
                **(task.requirements_json or {}),
                "confirmed_operation": "revenue_by_product",
                "confirmed_input": {
                    "kind": "csv", "sha256": item.sha256,
                    "version": item.version, "column_mapping": mapping,
                },
            }
            append_event(
                db, execution_id, event_key=f"input.columns_confirmed.v{item.version}",
                stage="column_mapping", event_type="column_mapping_confirmed",
                message=f"Confirmed {body.product_column} as product and {body.revenue_column} as revenue.",
                payload={"column_mapping": mapping, "sha256": item.sha256},
            )
            execution.status = "queued"
            execution.current_stage = "skill_discovery"
            append_event(
                db, execution_id, event_key=f"input.discovery_queued.v{item.version}",
                stage="skill_discovery", event_type="execution_queued",
                message="Inputs confirmed. Queued for skill discovery.",
                payload={"operation": "revenue_by_product"},
            )
            db.flush()
            result = output(item)
        return result
    except SQLAlchemyError as error:
        raise database_error(error) from None
