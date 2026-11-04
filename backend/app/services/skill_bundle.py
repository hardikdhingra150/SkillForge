"""Portable skill bundles: one JSON file with the code, contract, evidence, lineage and every fixture.

Import treats a bundle as untrusted: the hash must match the code and contract,
the code must pass the sandbox policy, and every fixture must pass again in the
sandbox before anything is stored.
"""

from datetime import UTC, datetime

from sqlalchemy import select

from app.database.skill_models import SkillVersion
from app.sandbox import check_source
from app.schemas.skill_contract import SkillContract
from app.services.repair import decode_fixture, encode_fixture, lineage_fixtures
from app.services.skill_registry import implementation_hash, run_fixture_tests, version_key

FORMAT = "skillforge.skill/v1"
MAX_FIXTURES = 50


class BundleError(ValueError):
    pass


def export_bundle(db, skill: SkillVersion) -> dict:
    if skill.source_code is None:
        raise BundleError("This version has no stored source to export.")
    lineage, node, seen = [], skill, set()
    while node is not None and node.version not in seen:
        seen.add(node.version)
        lineage.append({"version": node.version, "origin": node.origin, "parent_version": node.parent_version,
                        "summary": (node.change_json or {}).get("summary"), "implementation_hash": node.implementation_hash})
        node = db.get(SkillVersion, (skill.skill_id, node.parent_version)) if node.parent_version else None
    return {
        "format": FORMAT,
        "exported_at": datetime.now(UTC).isoformat(),
        "skill": {
            "skill_id": skill.skill_id, "version": skill.version, "capability": skill.capability, "origin": skill.origin,
            "parent_version": skill.parent_version, "contract": skill.contract_json, "source": skill.source_code,
            "implementation_hash": skill.implementation_hash, "validation": skill.validation_json,
        },
        "lineage": lineage,
        "fixtures": [encode_fixture(*fixture) for fixture in lineage_fixtures(db, skill)][:MAX_FIXTURES],
    }


def import_bundle(db, bundle: dict) -> tuple[SkillVersion, bool]:
    """Validate and store a bundle. Returns (row, created); an identical existing version is returned as-is."""
    if not isinstance(bundle, dict) or bundle.get("format") != FORMAT:
        raise BundleError(f"Not a SkillForge skill bundle (expected format {FORMAT}).")
    skill = bundle.get("skill") or {}
    source, contract_data = skill.get("source"), skill.get("contract")
    if not isinstance(source, str) or not isinstance(contract_data, dict):
        raise BundleError("The bundle is missing the skill's source or contract.")
    contract = SkillContract.model_validate(contract_data)
    check_source(source)
    fingerprint = implementation_hash(source, contract_data)
    if fingerprint != skill.get("implementation_hash"):
        raise BundleError("The bundle's implementation hash does not match its code and contract; it may have been edited.")
    fixtures = [decode_fixture(item) for item in (bundle.get("fixtures") or [])[:MAX_FIXTURES]]
    if not fixtures:
        raise BundleError("The bundle has no fixtures, so the skill cannot be proven here.")
    evidence = run_fixture_tests(source, contract_data, fixtures)

    skill_id = str(skill.get("skill_id") or contract.capability)[:80]
    versions = db.scalars(select(SkillVersion).where(SkillVersion.skill_id == skill_id)).all()
    same = next((v for v in versions if v.implementation_hash == fingerprint), None)
    if same is not None:
        return same, False
    wanted = str(skill.get("version") or "1.0.0")
    taken = {v.version for v in versions}
    if wanted in taken:
        major, minor = max(version_key(v) for v in taken)[:2]
        wanted = f"{major}.{minor + 1}.0"
    row = SkillVersion(
        skill_id=skill_id, version=wanted, capability=contract.capability, status="retired",
        implementation_hash=fingerprint, validation_json={**evidence, "imported": True}, source_code=source,
        contract_json=contract_data, origin="imported", parent_version=None,
        change_json={"imported_from": {"skill_id": skill.get("skill_id"), "version": skill.get("version"),
                                       "origin": skill.get("origin"), "exported_at": bundle.get("exported_at"),
                                       "lineage": bundle.get("lineage", [])},
                     "summary": f"Imported from a bundle and re-proven with {evidence['test_count']} fixtures.",
                     "fixtures": [encode_fixture(*f) for f in fixtures]},
    )
    db.add(row)
    db.flush()
    return row, True
