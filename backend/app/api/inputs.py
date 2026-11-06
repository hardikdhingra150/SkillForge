import hashlib
import logging
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import DB
from app.database.input_models import ExecutionCSVInput
from app.database.models import Execution, Task
from app.security import WorkspaceId, require_access
from app.services.csv_inputs import MAX_XLSX_BYTES, parse_csv, xlsx_to_csv
from app.services.events import append_event
from app.services.workflows import WORKFLOWS, describe_mapping, suggest_mapping, validate_columns

logger = logging.getLogger("uvicorn.error")
router = APIRouter(
    prefix="/api/v1", tags=["Task inputs"],
    dependencies=[Depends(require_access)],
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
    workflow: dict | None = None
    suggested_mapping: dict[str, str] = {}


class MappingConfirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    file_version: int = Field(ge=1)
    # {role: header} for the task's workflow, e.g. {"group": "Region", "amount": "Total"}.
    columns: dict[str, str] | None = Field(default=None, max_length=10)
    # Older clients (revenue by product only).
    product_column: str | None = Field(default=None, min_length=1, max_length=120)
    revenue_column: str | None = Field(default=None, min_length=1, max_length=120)

    def mapping(self) -> dict:
        if self.columns is not None:
            return {role: header.strip() and header for role, header in self.columns.items()}
        return {"product": self.product_column or "", "revenue": self.revenue_column or ""}


def workflow_of(task):
    return ((task.requirements_json or {}).get("review") or {}).get("candidate_workflow")


def output(item, task=None):
    workflow_id = workflow_of(task) if task is not None else None
    workflow = WORKFLOWS.get(workflow_id)
    suggested = {}
    if workflow is not None and item.confirmed_at is None:
        try:
            headers, rows = parse_csv(item.content_bytes)
            suggested = suggest_mapping(workflow.id, headers, rows, task.requirement)
        except ValueError:
            suggested = {}
    return CSVInputOut(
        execution_id=item.execution_id, filename=item.filename,
        sha256=item.sha256, version=item.version,
        headers=item.headers_json, row_count=item.row_count,
        preview=item.preview_json, column_mapping=item.mapping_json,
        confirmed=item.confirmed_at is not None,
        workflow=workflow.public() if workflow else None, suggested_mapping=suggested,
    )


def execution_row(db, execution_id, workspace_id, *, lock=False):
    statement = select(Execution, Task).join(Task, Task.id == Execution.task_id).where(
        Execution.id == execution_id, Task.workspace_id == workspace_id,
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
def get_input(execution_id: UUID, db: DB, workspace_id: WorkspaceId):
    try:
        _execution, task = execution_row(db, execution_id, workspace_id)
        item = db.get(ExecutionCSVInput, execution_id)
        if item is None:
            raise HTTPException(404, "No file has been uploaded for this task.")
        return output(item, task)
    except SQLAlchemyError as error:
        raise database_error(error) from None


@router.post("/executions/{execution_id}/input", response_model=CSVInputOut, status_code=201)
def upload_input(
    execution_id: UUID, db: DB, response: Response, workspace_id: WorkspaceId,
    file: Annotated[UploadFile, File()],
):
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    kind = filename.casefold().rsplit(".", 1)[-1] if "." in filename else ""
    if kind not in {"csv", "xlsx"}:
        raise HTTPException(422, "Choose a .csv or .xlsx file. Older .xls files: save them as .xlsx or CSV first.")
    filename = "".join(char for char in filename if char.isprintable())[:200]
    content = file.file.read(MAX_XLSX_BYTES + 1)
    try:
        if kind == "xlsx":
            content = xlsx_to_csv(content)
        headers, rows = parse_csv(content)
    except ValueError as error:
        raise HTTPException(422, str(error)) from None
    digest = hashlib.sha256(content).hexdigest()

    try:
        with db.begin():
            execution, task = execution_row(db, execution_id, workspace_id, lock=True)
            workflow = WORKFLOWS.get(workflow_of(task))
            if workflow is None:
                raise HTTPException(409, "This task needs clarification before accepting a file.")
            item = db.get(ExecutionCSVInput, execution_id)
            if item is not None and item.sha256 == digest:
                response.status_code = 200
                return output(item, task)
            if execution.status != "waiting_input" or execution.current_stage not in {"awaiting_input", "column_mapping"}:
                raise HTTPException(409, "This task is not accepting a new file. Start a new task to use different input.")
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
            item.uploaded_at = datetime.now(UTC)
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
                message=f"Read {len(rows)} data rows and {len(headers)} columns. "
                        + ("Confirm the suggested columns." if workflow.roles else "Confirm to run it."),
                payload={"headers": headers, "row_count": len(rows), "converted_from": "xlsx" if kind == "xlsx" else None},
            )
            db.flush()
            result = output(item, task)
        return result
    except SQLAlchemyError as error:
        raise database_error(error) from None


@router.post("/executions/{execution_id}/input/confirm", response_model=CSVInputOut)
def confirm_input(execution_id: UUID, body: MappingConfirm, db: DB, workspace_id: WorkspaceId):
    try:
        with db.begin():
            execution, task = execution_row(db, execution_id, workspace_id, lock=True)
            item = db.get(ExecutionCSVInput, execution_id)
            if item is None:
                raise HTTPException(409, "Upload a file before confirming columns.")
            if item.sha256 != body.file_sha256 or item.version != body.file_version:
                raise HTTPException(409, "The uploaded file changed. Refresh the page and confirm its current columns.")
            workflow = WORKFLOWS.get(workflow_of(task))
            if workflow is None:
                raise HTTPException(409, "This task has no workflow to run.")
            try:
                headers, rows = parse_csv(item.content_bytes)
                mapping = validate_columns(workflow.id, headers, rows, body.mapping())
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            if item.confirmed_at is not None:
                if item.mapping_json == mapping:
                    return output(item, task)
                raise HTTPException(409, "These columns are already confirmed. Start a new task to use a different mapping.")
            if execution.status != "waiting_input" or execution.current_stage != "column_mapping":
                raise HTTPException(409, "This task is not waiting for column confirmation.")
            item.mapping_json = mapping
            item.confirmed_at = datetime.now(UTC)
            task.requirements_json = {
                **(task.requirements_json or {}),
                "confirmed_operation": workflow.id,
                "confirmed_input": {
                    "kind": "csv", "sha256": item.sha256,
                    "version": item.version, "column_mapping": mapping,
                },
            }
            append_event(
                db, execution_id, event_key=f"input.columns_confirmed.v{item.version}",
                stage="column_mapping", event_type="column_mapping_confirmed",
                message=f"Confirmed the columns for {workflow.title.lower()}: {describe_mapping(workflow.id, mapping)}.",
                payload={"column_mapping": mapping, "sha256": item.sha256, "workflow": workflow.id},
            )
            execution.status = "queued"
            execution.current_stage = "skill_discovery"
            append_event(
                db, execution_id, event_key=f"input.discovery_queued.v{item.version}",
                stage="skill_discovery", event_type="execution_queued",
                message="Inputs confirmed. Queued for skill discovery.",
                payload={"operation": workflow.id},
            )
            db.flush()
            result = output(item, task)
        return result
    except SQLAlchemyError as error:
        raise database_error(error) from None


class ClarificationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer: str = Field(min_length=1, max_length=2000)


MAX_REVIEW_ROUNDS = 5


@router.post("/executions/{execution_id}/clarify", status_code=202)
def clarify_requirement(execution_id: UUID, body: ClarificationIn, db: DB, workspace_id: WorkspaceId):
    """Answer the reviewer's question; the request is queued for another review round."""
    try:
        with db.begin():
            execution, task = execution_row(db, execution_id, workspace_id, lock=True)
            meta = dict(task.requirements_json or {})
            review = meta.get("review", {})
            if execution.status != "waiting_input" or review.get("next_action") != "clarify_requirement":
                raise HTTPException(409, "This run is not waiting for a clarification.")
            rounds = meta.get("review_round", 1) + 1
            if rounds > MAX_REVIEW_ROUNDS:
                raise HTTPException(409, "Too many clarification rounds. Start a new task with a fuller description.")
            answer = body.answer.strip()
            task.requirements_json = {**meta, "review_round": rounds,
                                      "clarifications": [*meta.get("clarifications", []), answer]}
            execution.status, execution.current_stage = "queued", "admission"
            append_event(db, execution.id, event_key=f"review.clarify.{rounds}", stage="admission",
                         event_type="clarification_received", message=f"Clarification received: {answer[:200]}",
                         payload={"answer": answer, "round": rounds})
        return {"execution_id": str(execution_id), "status": "queued", "round": rounds}
    except SQLAlchemyError as error:
        raise database_error(error) from None
