"""Registry operations: hashing, version selection, fixture tests and registration."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.database.skill_models import SkillVersion
from app.sandbox import run_skill
from app.schemas.skill_contract import SkillContract
from app.security import LOCAL_WORKSPACE_ID
from app.services.checks import run_checks


class SkillIntegrityError(ValueError):
    pass


class ExampleMismatch(ValueError):
    """A worked example's expected output disagrees with what the code returned."""

    def __init__(self, name, inputs, output, expected):
        wrong = {key: output.get(key) for key in expected if output.get(key) != expected[key]}
        super().__init__(f"Example {name} returned {wrong}, expected { {k: expected[k] for k in wrong} }.")
        self.name, self.inputs, self.output, self.expected = name, inputs, output, expected


def canonical_contract(contract: dict) -> bytes:
    return json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()


def implementation_hash(source: str, contract: dict) -> str:
    """Fingerprint of exactly what runs: the stored source plus its contract."""
    return hashlib.sha256(b"skillforge-skill-v1\0" + source.encode() + b"\0" + canonical_contract(contract)).hexdigest()


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def visible_to(workspace_id):
    """Skills a workspace can see and run: the shared ones plus its own."""
    return or_(SkillVersion.workspace_id.is_(None), SkillVersion.workspace_id == workspace_id)


def can_see(skill: SkillVersion | None, workspace_id) -> bool:
    return skill is not None and skill.workspace_id in (None, workspace_id)


def owner_for(workspace_id):
    """Who a newly created or repaired version belongs to: the owner's are shared, a visitor's stay private."""
    return None if workspace_id in (None, LOCAL_WORKSPACE_ID) else workspace_id


def latest_validated(db, capability: str, workspace_id=LOCAL_WORKSPACE_ID) -> SkillVersion | None:
    """The newest validated, runnable (stored-source) version for a capability that this workspace can see."""
    rows = db.scalars(
        select(SkillVersion).where(
            visible_to(workspace_id),
            SkillVersion.capability == capability,
            SkillVersion.status == "validated",
            SkillVersion.source_code.is_not(None),
        ).with_for_update(read=True)
    ).all()
    return max(rows, key=lambda row: version_key(row.version), default=None)


def verify(skill: SkillVersion) -> SkillContract:
    """Refuse to run a version whose stored source or contract no longer matches its hash."""
    if skill.source_code is None or skill.contract_json is None:
        raise SkillIntegrityError(f"{skill.skill_id} v{skill.version} has no stored source.")
    if implementation_hash(skill.source_code, skill.contract_json) != skill.implementation_hash:
        raise SkillIntegrityError(f"{skill.skill_id} v{skill.version} does not match its implementation hash.")
    if skill.validation_json.get("passed") is not True:
        raise SkillIntegrityError(f"{skill.skill_id} v{skill.version} has no passing validation evidence.")
    return SkillContract.model_validate(skill.contract_json)


def run_fixture_tests(source: str, contract_data: dict, fixtures) -> dict:
    """Run every fixture through the sandbox and the contract checks. Raises on the first failure."""
    contract = SkillContract.model_validate(contract_data)
    evidence = []
    for name, inputs, files, expected in fixtures:
        result = run_skill(source, inputs=inputs, files=files, tools=contract.tools)
        if expected is None:
            if result.ok:
                raise ValueError(f"Fixture {name} should have failed but passed.")
            evidence.append({"name": name, "passed": True})
            continue
        if not result.ok:
            raise ValueError(f"Fixture {name} failed: {result.error['message']}")
        run_checks(contract, files, inputs, result.output)
        if expected == "checks":  # recorded real input: the contract checks are the oracle
            evidence.append({"name": name, "passed": True})
            continue
        if "output" in expected:  # worked example: every expected field must match exactly
            if any(result.output.get(key) != value for key, value in expected["output"].items()):
                raise ExampleMismatch(name, inputs, result.output, expected["output"])
            evidence.append({"name": name, "passed": True})
            continue
        totals = {item["product"]: Decimal(item["revenue"]) for item in result.output.get("products", [])}
        want = {key: Decimal(value) for key, value in expected.get("totals", {}).items()}
        if totals != want or Decimal(result.output["total_revenue"]) != Decimal(expected["total_revenue"]):  # sales fixtures
            raise ValueError(f"Fixture {name} returned the wrong totals.")
        evidence.append({"name": name, "passed": True})
    return {"passed": True, "test_count": len(evidence), "tests": evidence, "runner": "sandbox"}


def register_builtin(db, skill) -> dict:
    """Insert a built-in version, or backfill a legacy row that predates stored source.

    Registered versions are immutable: if the row already holds different
    source, contract or evidence, this refuses instead of overwriting.
    """
    evidence = run_fixture_tests(skill.source, skill.contract, skill.fixtures)
    fingerprint = implementation_hash(skill.source, skill.contract)
    db.execute(
        insert(SkillVersion).values(
            skill_id=skill.skill_id, version=skill.version, capability=skill.contract["capability"],
            status="validated", implementation_hash=fingerprint, validation_json=evidence,
            source_code=skill.source, contract_json=skill.contract, origin="builtin",
        ).on_conflict_do_nothing(index_elements=["skill_id", "version"])
    )
    existing = db.get(SkillVersion, (skill.skill_id, skill.version))
    if existing.origin in ("generated", "repaired", "imported"):
        # A skill with this id was created in this workspace before the starter pack shipped: keep it.
        return {**evidence, "skipped": f"kept the existing {existing.origin} {skill.skill_id} v{skill.version}"}
    if existing.source_code is None:
        # One-time upgrade of a row registered before skills were stored as source.
        existing.change_json = {"backfill": {
            "previous_implementation_hash": existing.implementation_hash,
            "reason": "Stored the skill's source and contract for sandboxed execution.",
        }}
        existing.implementation_hash = fingerprint
        existing.validation_json = evidence
        existing.source_code = skill.source
        existing.contract_json = skill.contract
        existing.origin = "builtin"
        db.flush()
    elif existing.implementation_hash != fingerprint or existing.status != "validated" or existing.validation_json != evidence:
        raise ValueError(
            f"{skill.skill_id} v{skill.version} already has different code, status, or validation evidence. "
            "Register a new version instead of overwriting it."
        )
    return evidence
