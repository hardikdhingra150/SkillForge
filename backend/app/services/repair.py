"""Diagnose a failed skill run, patch the skill, prove the patch, and promote a new version.

A repair is only accepted when the patched skill:
  1. passes the static sandbox policy and a valid contract,
  2. succeeds on the input that failed, including every contract check,
  3. passes every fixture in its lineage (built-in fixtures plus earlier repairs' fixtures),
  4. passes the fixtures the strategy itself supplies as proof of the fix.
Only then is it stored as a new, immutable, validated version that later runs reuse.
"""

import base64
import difflib
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database.skill_models import SkillVersion
from app.sandbox import PolicyViolation, check_source, run_skill
from app.sandbox.tools import loose
from app.schemas.skill_contract import SkillContract
from app.services import audit
from app.services.checks import CheckFailed, run_checks
from app.services.skill_registry import can_see, implementation_hash, owner_for, run_fixture_tests, version_key
from app.skills import BUILTIN_SKILLS

MAX_FIXTURE_BYTES = 256 * 1024


@dataclass(frozen=True)
class Failure:
    code: str
    message: str
    details: dict = field(default_factory=dict)

    def payload(self):
        return {"code": self.code, "message": self.message, "details": self.details}


def classify_run_error(error: dict) -> Failure:
    """Turn a sandbox error into a typed failure. Tool errors carry their own code."""
    if error.get("code"):
        return Failure(error["code"], error["message"], error.get("details") or {})
    if error.get("type") == "Timeout":
        return Failure("TIMEOUT", error["message"])
    return Failure("SKILL_ERROR", error.get("message", "The skill failed."), {"type": error.get("type")})


def classify_check(error: CheckFailed) -> Failure:
    return Failure("CHECK_FAILED", str(error), {"check": error.check})


# ---------- Strategies ----------

@dataclass(frozen=True)
class Patch:
    source: str
    contract: dict
    summary: str
    fixtures: list  # (name, inputs, files, expected) proving the fix


# Proof files per capability: a small input with the problem a strategy fixes. The host reference checks are the
# oracle ("checks"), so the proof holds for any correct implementation.
AMOUNT_PROOFS = {
    "totals_by_group": ({"group_column": "Region", "amount_column": "Amount"},
                        b'Region,Amount\nNorth,"$1,200.50"\nSouth,(300)\nNorth,-\xe2\x82\xac100\n'),
    "totals_by_month": ({"date_column": "Date", "amount_column": "Amount"},
                        b'Date,Amount\n2026-01-02,"$1,200.50"\n2026-02-03,(300)\n'),
}
DATE_PROOFS = {
    "totals_by_month": ({"date_column": "Date", "amount_column": "Amount"},
                        b'Date,Amount\n03/15/2026,1\n15 Mar 2026,2\n2026-04-01,3\n"Apr 2, 2026",4\n'),
}


def proof(table, contract, name):
    item = table.get(contract["capability"])
    if item is None:
        return []
    mapping, content = item
    files = {next(f["name"] for f in contract["inputs"] if f["type"] == "csv"): content}
    return [(name, mapping, files, "checks")]


def swap_tool(source, contract, old, new):
    """Replace calls to one tool with another, and the contract's tool list to match."""
    new_source = source.replace(f"tools.{old}(", f"tools.{new}(")
    tools = [name for name in contract["tools"] if name != old or f"tools.{old}(" in new_source]
    if new not in tools:
        tools.append(new)
    return new_source, {**contract, "tools": tools}


class NormalizeAmounts:
    """BAD_NUMBER: the skill parses amounts strictly; switch it to the export-aware parser."""

    name = "normalize_amounts"

    def applies(self, failure, source, contract):
        return failure.code == "BAD_NUMBER" and "tools.to_decimal(" in source and "parse_amount" not in contract["tools"]

    def patch(self, failure, source, contract):
        new_source, new_contract = swap_tool(source, contract, "to_decimal", "parse_amount")
        if contract["capability"] == "revenue_by_product":
            proof_csv = b'Product,Sales\nPen,"$1,200.50"\nBook,(300)\nPen,-\xe2\x82\xac100\nCard,"\xc2\xa32,000"\n'
            mapping = {"product_column": "Product", "revenue_column": "Sales"}
            fixtures = [("repair_formatted_amounts", mapping, {"sales_csv": proof_csv},
                         {"totals": {"Pen": "1100.50", "Book": "-300", "Card": "2000"}, "total_revenue": "2800.50"})]
        else:
            fixtures = proof(AMOUNT_PROOFS, contract, "repair_formatted_amounts")
        return Patch(
            source=new_source,
            contract=new_contract,
            summary=f"Amounts like {failure.details.get('value', 'the failing value')!r} are export-formatted. "
                    "Parse them with parse_amount (currency symbols, thousands separators, parentheses negatives).",
            fixtures=fixtures,
        )


class NormalizeDates:
    """DATE_FORMAT: the skill only reads ISO dates; switch it to the exported-date parser."""

    name = "normalize_dates"

    def applies(self, failure, source, contract):
        return failure.code == "DATE_FORMAT" and "tools.iso_dates(" in source and "parse_dates" not in contract["tools"]

    def patch(self, failure, source, contract):
        new_source, new_contract = swap_tool(source, contract, "iso_dates", "parse_dates")
        return Patch(
            source=new_source, contract=new_contract,
            summary=f"Dates like {failure.details.get('value', 'the failing value')!r} are not ISO. Read them with "
                    "parse_dates (15/03/2026, 03/15/2026, 15 Mar 2026, Mar 15, 2026; day/month order from the column).",
            fixtures=proof(DATE_PROOFS, contract, "repair_exported_dates"),
        )


class MatchColumnsLoosely:
    """MISSING_COLUMN: the requested header differs only in case, spaces, underscores or hyphens."""

    name = "match_columns_loosely"

    def applies(self, failure, source, contract):
        if failure.code != "MISSING_COLUMN" or "tools.column(" not in source or "find_column" in contract["tools"]:
            return False
        wanted, available = failure.details.get("column"), failure.details.get("available") or []
        return wanted is not None and sum(loose(header) == loose(wanted) for header in available) == 1

    def patch(self, failure, source, contract):
        new_source, new_contract = swap_tool(source, contract, "column", "find_column")
        wanted = failure.details.get("column")
        actual = next(h for h in failure.details.get("available", []) if loose(h) == loose(wanted))
        return Patch(
            source=new_source, contract=new_contract,
            summary=f"The file calls the column {actual!r}, not {wanted!r}. Look columns up with find_column, which "
                    "ignores case, surrounding spaces, underscores and hyphens (and refuses ambiguous matches).",
            fixtures=[],
        )


STRATEGIES = [NormalizeAmounts(), NormalizeDates(), MatchColumnsLoosely()]


# ---------- Fixtures across a skill's lineage ----------

def encode_fixture(name, inputs, files, expected):
    return {"name": name, "inputs": inputs, "files": {k: base64.b64encode(v).decode() for k, v in files.items()},
            "expected": expected}


def decode_fixture(item):
    return (item["name"], item["inputs"], {k: base64.b64decode(v) for k, v in item["files"].items()}, item["expected"])


def lineage_fixtures(db, skill) -> list:
    """Built-in fixtures for the skill plus every fixture recorded by repairs along its lineage."""
    fixtures, seen, node = [], set(), skill
    while node is not None and node.version not in seen:
        seen.add(node.version)
        fixtures.extend(decode_fixture(item) for item in (node.change_json or {}).get("fixtures", []))
        node = db.get(SkillVersion, (skill.skill_id, node.parent_version)) if node.parent_version else None
    builtin = next((b for b in BUILTIN_SKILLS if b.skill_id == skill.skill_id), None)
    return (builtin.fixtures if builtin else []) + fixtures


def failing_input_fixture(version, inputs, files):
    """Keep the input that triggered the repair as a regression fixture, if it is small enough to store."""
    if sum(len(data) for data in files.values()) > MAX_FIXTURE_BYTES:
        return None
    return (f"regression_input_for_v{version}", inputs, files, "checks")


# ---------- Versioning ----------

def next_version(db, skill_id: str, parent: str) -> str:
    major, minor = version_key(parent)[:2]
    while True:
        minor += 1
        candidate = f"{major}.{minor}.0"
        if db.get(SkillVersion, (skill_id, candidate)) is None:
            return candidate


def retired_duplicate(db, skill_id, source, contract):
    """A version with exactly this code that a reviewer retired, if any: retired code must not come back."""
    fingerprint = implementation_hash(source, contract)
    return db.scalars(select(SkillVersion).where(SkillVersion.skill_id == skill_id, SkillVersion.status == "retired",
                                                 SkillVersion.implementation_hash == fingerprint)).first()


def promote(db, parent, source, contract, evidence, change, actor: str = "worker", workspace_id=None) -> SkillVersion:
    """Insert the repaired version and audit it. If another worker promoted the same fix first, reuse it."""
    fingerprint = implementation_hash(source, contract)
    for _ in range(5):
        version = next_version(db, parent.skill_id, parent.version)
        inserted = db.execute(
            insert(SkillVersion).values(
                skill_id=parent.skill_id, version=version, capability=parent.capability, status="validated",
                implementation_hash=fingerprint, validation_json=evidence, source_code=source, contract_json=contract,
                origin="repaired", parent_version=parent.version, change_json=change,
                workspace_id=owner_for(workspace_id),
            ).on_conflict_do_nothing(index_elements=["skill_id", "version"])
        ).rowcount
        row = db.get(SkillVersion, (parent.skill_id, version))
        if inserted:
            audit.record(db, actor=actor, action="skill.promoted", target=audit.skill_target(row.skill_id, row.version),
                         reason=change.get("summary") or f"Repaired from v{parent.version}.",
                         details={"parent_version": parent.version, "strategy": change.get("strategy"),
                                  "failure": (change.get("failure") or {}).get("code"),
                                  "tests": evidence.get("test_count"), "implementation_hash": fingerprint},
                         **({"workspace_id": workspace_id} if workspace_id else {}))
        # Someone else promoted the same fix first: reuse it, unless it is another visitor's private version.
        if inserted or (row.implementation_hash == fingerprint and can_see(row, workspace_id)):
            return row
    raise RuntimeError("Could not allocate a version for the repaired skill.")


# ---------- The loop ----------

@dataclass
class Repaired:
    skill: SkillVersion
    contract: SkillContract
    output: dict
    validation: dict


@dataclass
class Exhausted:
    attempts: list
    last_failure: Failure


def attempt_repair(db, emit, skill, inputs, files, failure: Failure, budget: int, actor: str = "worker",
                   workspace_id=None):
    """Try up to `budget` strategies. Returns Repaired, or Exhausted for human review.

    When a patch fixes the diagnosed problem but the run then hits a different problem another strategy can fix,
    the next strategy builds on that patch, so a file with two problems gets both fixes in one new version.
    """
    source, contract = skill.source_code, skill.contract_json
    attempts, tried, diagnosed, applied = [], set(), failure, []
    emit("repair_started", "repair", f"Diagnosed {failure.code}. Starting repair (budget: {budget} attempts).",
         {"failure": failure.payload(), "budget": budget})

    while len(attempts) < budget:
        strategy = next((s for s in STRATEGIES if s.name not in tried and s.applies(failure, source, contract)), None)
        if strategy is None:
            break
        tried.add(strategy.name)
        patch = strategy.patch(failure, source, contract)
        version_hint = next_version(db, skill.skill_id, skill.version)
        diff = "".join(difflib.unified_diff(
            skill.source_code.splitlines(keepends=True), patch.source.splitlines(keepends=True),
            fromfile=f"{skill.skill_id} v{skill.version}", tofile=f"{skill.skill_id} v{version_hint}",
        ))
        emit("repair_candidate", "repair", f"Attempt {len(attempts) + 1}: {strategy.name}. {patch.summary}",
             {"strategy": strategy.name, "summary": patch.summary, "diff": diff, "tools": patch.contract["tools"]})

        builds_on = False
        try:
            check_source(patch.source)
            candidate_contract = SkillContract.model_validate(patch.contract)
            run = run_skill(patch.source, inputs=inputs, files=files, tools=candidate_contract.tools)
            if not run.ok:
                next_failure = classify_run_error(run.error)
                builds_on = next_failure.code != failure.code and any(
                    s.name not in tried and s.applies(next_failure, patch.source, patch.contract) for s in STRATEGIES)
                raise _AttemptFailed(next_failure)
            try:
                validation = run_checks(candidate_contract, files, inputs, run.output)
            except CheckFailed as error:
                raise _AttemptFailed(classify_check(error)) from None
            proofs = [fixture for earlier in applied for fixture in earlier[1].fixtures] + patch.fixtures
            fixtures = lineage_fixtures(db, skill) + proofs
            regression = failing_input_fixture(version_hint, inputs, files)
            if regression:
                fixtures.append(regression)
            try:
                evidence = run_fixture_tests(patch.source, patch.contract, fixtures)
            except (ValueError, CheckFailed) as error:
                raise _AttemptFailed(Failure("REGRESSION", str(error))) from None
            retired = retired_duplicate(db, skill.skill_id, patch.source, patch.contract)
            if retired is not None:
                raise _AttemptFailed(Failure("RETIRED_FIX", f"This fix is identical to v{retired.version}, which a reviewer retired."))
        except PolicyViolation as error:
            failure = Failure("POLICY_VIOLATION", str(error))
        except _AttemptFailed as error:
            failure = error.failure
        else:
            steps = [*applied, (strategy, patch)]
            new_fixtures = proofs + ([regression] if regression else [])
            change = {
                "strategy": "+".join(step.name for step, _ in steps),
                "summary": " ".join(item.summary for _, item in steps), "diff": diff,
                "failure": diagnosed.payload(), "attempts": len(attempts) + 1,
                "fixtures": [encode_fixture(*fixture) for fixture in new_fixtures],
            }
            new = promote(db, skill, patch.source, patch.contract,
                          {**evidence, "repaired_from": skill.version}, change, actor=actor, workspace_id=workspace_id)
            emit("repair_applied", "repair", f"The patched skill passed {evidence['test_count']} tests and all contract checks.",
                 {"strategy": change["strategy"], "tests": evidence["tests"]})
            emit("skill_promoted", "versioning", f"Saved {new.skill_id} v{new.version} (repaired from v{skill.version}). "
                 "Future runs will reuse it.",
                 {"skill_id": new.skill_id, "version": new.version, "parent_version": skill.version,
                  "implementation_hash": new.implementation_hash})
            return Repaired(new, candidate_contract, run.output, validation)

        attempts.append({"strategy": strategy.name, "failure": failure.payload()})
        if builds_on:
            applied.append((strategy, patch))
            source, contract = patch.source, patch.contract
            emit("repair_progress", "repair", f"{strategy.name} fixed that, and the file also has {failure.code}: "
                 f"{failure.message} Building the next fix on top of it.",
                 {"strategy": strategy.name, "failure": failure.payload()})
            continue
        emit("repair_rejected", "repair", f"{strategy.name} did not fix it: {failure.message}",
             {"strategy": strategy.name, "failure": failure.payload()})

    emit("repair_exhausted", "repair",
         f"No automatic repair succeeded after {len(attempts)} attempt(s). A person needs to review this run.",
         {"attempts": attempts, "last_failure": failure.payload(), "budget": budget})
    return Exhausted(attempts, failure)


class _AttemptFailed(Exception):
    def __init__(self, failure: Failure):
        super().__init__(failure.message)
        self.failure = failure
