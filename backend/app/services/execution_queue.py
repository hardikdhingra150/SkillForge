import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.input_models import ExecutionCSVInput
from app.database.models import Execution, Task
from app.sandbox import PolicyViolation, run_skill
from app.services.checks import CheckFailed, run_checks
from app.services.events import append_event
from app.services.repair import Exhausted, attempt_repair, classify_check, classify_run_error
from app.services.skill_registry import latest_validated, verify


def bind_inputs(contract, item):
    """Map the confirmed CSV and column mapping onto the contract's declared inputs.

    A `csv` input receives the confirmed file; a `<key>_column` input receives
    mapping[key] (e.g. product_column <- mapping["product"]).
    """
    inputs, files = {}, {}
    for field in contract.inputs:
        if field.type == "csv":
            files[field.name] = item.content_bytes
        elif field.type == "column":
            key = field.name.removesuffix("_column")
            if key not in item.mapping_json and not field.required:
                continue
            if key not in item.mapping_json:
                raise ValueError(f"The confirmed mapping has no column for {field.name}.")
            inputs[field.name] = item.mapping_json[key]
        elif field.required:
            raise ValueError(f"The contract input {field.name} ({field.type}) cannot be bound from a CSV task.")
    return inputs, files


def execute_next(db):
    if not db.in_transaction():
        raise RuntimeError("Call execute_next inside an explicit transaction.")
    execution = db.scalars(
        select(Execution).join(Task, Task.id == Execution.task_id)
        .where(
            Execution.status == "queued",
            Execution.current_stage == "skill_discovery",
        )
        .order_by(Execution.created_at, Execution.id).limit(1)
        .with_for_update(of=Execution, skip_locked=True)
    ).first()
    if execution is None:
        return None

    task = db.get(Task, execution.task_id)
    run_attempt = (task.requirements_json or {}).get("run_attempt", 1)
    prefix = "run.v1" if run_attempt == 1 else f"run.v1.retry{run_attempt}"

    seen_kinds = {}

    def emit(kind, stage, message, payload=None):
        # Repairs can emit the same kind more than once (one candidate per attempt): number the repeats.
        seen_kinds[kind] = seen_kinds.get(kind, 0) + 1
        suffix = "" if seen_kinds[kind] == 1 else f".{seen_kinds[kind]}"
        execution.current_stage = stage
        append_event(
            db, execution.id, event_key=f"{prefix}.{kind}{suffix}", stage=stage,
            event_type=kind, message=message, payload=payload,
        )

    execution.status = "running"
    execution.started_at = execution.started_at or datetime.now(UTC)
    db.flush()
    emit("execution_started", "skill_discovery", "A worker started processing the confirmed input.")

    try:
        task = db.get(Task, execution.task_id)
        item = db.get(ExecutionCSVInput, execution.id)
        confirmed = (task.requirements_json or {}).get("confirmed_input", {})
        capability = (task.requirements_json or {}).get("confirmed_operation")
        if item is None or item.confirmed_at is None:
            raise ValueError("A confirmed file is required.")
        if (
            hashlib.sha256(item.content_bytes).hexdigest() != item.sha256
            or confirmed.get("sha256") != item.sha256
            or confirmed.get("version") != item.version
            or confirmed.get("column_mapping") != item.mapping_json
        ):
            raise ValueError("The stored CSV no longer matches its confirmed input.")

        skill = latest_validated(db, capability) if capability else None
        if skill is None:
            raise ValueError(f"No validated skill is registered for {capability or 'this operation'}.")
        contract = verify(skill)
        inputs, files = bind_inputs(contract, item)

        selected = {"id": skill.skill_id, "version": skill.version, "implementation_hash": skill.implementation_hash}
        emit("skill_selected", "skill_discovery", f"Selected {skill.skill_id} v{skill.version} from the validated registry.", {
            **selected, "reason": f"Latest validated version for {capability}.",
            "source": "existing_registry", "origin": skill.origin,
            "registration_tests": skill.validation_json.get("test_count"),
        })
        execution.plan_json = {
            "skill": selected,
            "input": {"sha256": item.sha256, "version": item.version, "column_mapping": item.mapping_json},
            "steps": ["sandbox_run", *contract.checks],
            "tools": contract.tools,
        }
        emit("plan_created", "planning", "Prepared the sandboxed run and its validation checks.", execution.plan_json)

        emit("step_started", "execution", f"Running {skill.skill_id} v{skill.version} in the sandbox.")
        run = run_skill(skill.source_code, inputs=inputs, files=files, tools=contract.tools)
        failure = output = validation = None
        if run.ok:
            output = run.output
            rows = output.get("rows_processed")
            summary = f"Processed {rows} rows" if isinstance(rows, int) else "The skill finished"
            emit("step_completed", "execution", f"{summary} in {run.duration_ms:g} ms.", {"duration_ms": run.duration_ms})
            emit("validation_started", "validation", "Checking the output against the contract and reference calculations.")
            try:
                validation = run_checks(contract, files, inputs, output)
            except CheckFailed as error:
                failure = classify_check(error)
                emit("validation_failed", "validation", str(error), {"code": "OUTPUT_VALIDATION_FAILED", "check": error.check})
        else:
            failure = classify_run_error(run.error)
            emit("step_failed", "execution", f"The skill failed: {failure.message}", {"code": "SKILL_STEP_FAILED", "error": run.error})

        if failure is not None:
            budget = (task.requirements_json or {}).get("repair_budget", settings.repair_budget)
            outcome = attempt_repair(db, emit, skill, inputs, files, failure, budget, workspace_id=task.workspace_id)
            if isinstance(outcome, Exhausted):
                execution.status = "waiting_approval"
                execution.result_json = {"error": {
                    "code": "REPAIR_NEEDS_REVIEW", "message": outcome.last_failure.message,
                    "failure": outcome.last_failure.payload(), "attempts": outcome.attempts,
                }, "skill": selected}
                execution.finished_at = datetime.now(UTC)
                db.flush()
                return execution.id
            skill, contract, output, validation = outcome.skill, outcome.contract, outcome.output, outcome.validation
            selected = {"id": skill.skill_id, "version": skill.version, "implementation_hash": skill.implementation_hash,
                        "repaired_from": skill.parent_version}

        emit("validation_passed", "validation", "All contract checks passed.", validation)
        execution.result_json = {**output, "skill": selected, "input_sha256": item.sha256, "validation": validation}
        execution.status = "succeeded"
        emit("execution_completed", "completed", f"{capability.replace('_', ' ').capitalize()} completed successfully.", {
            key: output[key] for key in ("rows_processed", "total_revenue", "total", "kept", "removed") if key in output
        })
    except SQLAlchemyError:
        raise
    except Exception as error:
        message = str(error) if isinstance(error, ValueError) else "Skill execution or output validation failed."
        detail = {"code": "OUTPUT_VALIDATION_FAILED", "check": error.check} if isinstance(error, CheckFailed) else {}
        if isinstance(error, PolicyViolation):
            detail = {"code": "SKILL_POLICY_VIOLATION"}
        if execution.current_stage == "validation":
            emit("validation_failed", "validation", message, detail or {"code": "OUTPUT_VALIDATION_FAILED"})
        elif execution.current_stage == "execution":
            emit("step_failed", "execution", message, detail or {"code": "SKILL_STEP_FAILED"})
        execution.status = "failed"
        execution.result_json = {"error": {"code": "EXECUTION_FAILED", "message": message, **({"detail": detail} if detail else {})}}
        emit("execution_failed", "failed", message, {"code": "EXECUTION_FAILED"})

    execution.finished_at = datetime.now(UTC)
    db.flush()
    return execution.id
