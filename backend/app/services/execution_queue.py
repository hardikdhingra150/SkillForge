import hashlib
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.database.input_models import ExecutionCSVInput
from app.database.models import Execution, Task
from app.database.skill_models import SkillVersion
from app.services.builtin_sales import (
    IMPLEMENTATION_HASH, SKILL_ID, VERSION, run_sales, validate_sales_result,
)
from app.services.events import append_event
from app.services.request_queue import DEV_WORKSPACE_ID


def execute_next(db):
    if not db.in_transaction():
        raise RuntimeError("Call execute_next inside an explicit transaction.")
    execution = db.scalars(
        select(Execution).join(Task, Task.id == Execution.task_id)
        .where(
            Execution.status == "queued",
            Execution.current_stage == "skill_discovery",
            Task.workspace_id == DEV_WORKSPACE_ID,
        )
        .order_by(Execution.created_at, Execution.id).limit(1)
        .with_for_update(of=Execution, skip_locked=True)
    ).first()
    if execution is None:
        return None

    def emit(kind, stage, message, payload=None):
        execution.current_stage = stage
        append_event(
            db, execution.id, event_key=f"run.v1.{kind}", stage=stage,
            event_type=kind, message=message, payload=payload,
        )

    execution.status = "running"
    execution.started_at = execution.started_at or datetime.now(timezone.utc)
    db.flush()
    emit("execution_started", "skill_discovery", "A worker started processing the confirmed input.")

    try:
        task = db.get(Task, execution.task_id)
        item = db.get(ExecutionCSVInput, execution.id)
        confirmed = (task.requirements_json or {}).get("confirmed_input", {})
        if item is None or item.confirmed_at is None:
            raise ValueError("A confirmed CSV is required.")
        if (task.requirements_json or {}).get("confirmed_operation") != SKILL_ID:
            raise ValueError("The confirmed operation is unsupported.")
        if (
            hashlib.sha256(item.content_bytes).hexdigest() != item.sha256
            or confirmed.get("sha256") != item.sha256
            or confirmed.get("version") != item.version
            or confirmed.get("column_mapping") != item.mapping_json
        ):
            raise ValueError("The stored CSV no longer matches its confirmed input.")

        skill = db.scalars(
            select(SkillVersion).where(
                SkillVersion.skill_id == SKILL_ID,
                SkillVersion.version == VERSION,
                SkillVersion.capability == SKILL_ID,
                SkillVersion.status == "validated",
                SkillVersion.implementation_hash == IMPLEMENTATION_HASH,
            ).with_for_update(read=True)
        ).first()
        if skill is None or skill.validation_json.get("passed") is not True:
            raise ValueError("A validated installed revenue-by-product skill is unavailable.")

        selected = {"id": skill.skill_id, "version": skill.version, "implementation_hash": skill.implementation_hash}
        emit("skill_selected", "skill_discovery", f"Selected {SKILL_ID} v{VERSION} from the validated registry.", {
            **selected, "reason": "Supports the confirmed revenue-by-product operation and column mapping.",
            "source": "existing_registry", "registration_tests": skill.validation_json["test_count"],
        })
        execution.plan_json = {
            "skill": selected,
            "input": {"sha256": item.sha256, "version": item.version, "column_mapping": item.mapping_json},
            "steps": ["read_csv", "group_and_sum", "validate_result"],
        }
        emit("plan_created", "planning", "Prepared the CSV reading, aggregation, and validation plan.", execution.plan_json)
        emit("step_started", "execution", "Reading the CSV and aggregating revenue by product.")
        result = run_sales(item.content_bytes, item.mapping_json)
        emit("step_completed", "execution", f"Processed {result['rows_processed']} rows into {len(result['products'])} product groups.")
        emit("validation_started", "validation", "Checking row counts and calculated totals.")
        validation = validate_sales_result(item.content_bytes, item.mapping_json, result)
        emit("validation_passed", "validation", "Row counts, product totals, and the overall total passed validation.", validation)
        execution.result_json = {
            **result, "skill": selected, "input_sha256": item.sha256, "validation": validation,
        }
        execution.status = "succeeded"
        emit("execution_completed", "completed", "Revenue-by-product analysis completed successfully.", {
            "rows_processed": result["rows_processed"], "total_revenue": result["total_revenue"],
        })
    except SQLAlchemyError:
        raise
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else "Skill execution or output validation failed."
        if execution.current_stage == "validation":
            emit("validation_failed", "validation", message, {"code": "OUTPUT_VALIDATION_FAILED"})
        elif execution.current_stage == "execution":
            emit("step_failed", "execution", message, {"code": "SKILL_STEP_FAILED"})
        execution.status = "failed"
        execution.result_json = {"error": {"code": "EXECUTION_FAILED", "message": message}}
        emit("execution_failed", "failed", message, {"code": "EXECUTION_FAILED"})

    execution.finished_at = datetime.now(timezone.utc)
    db.flush()
    return execution.id
