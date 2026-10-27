from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.database.connection import engine
from app.database.session import SessionLocal
from app.database.skill_models import SkillVersion
from app.services.builtin_sales import IMPLEMENTATION_HASH, SKILL_ID, VERSION, run_self_tests


def register_skill(db):
    evidence = run_self_tests()
    db.execute(
        insert(SkillVersion).values(
            skill_id=SKILL_ID, version=VERSION, capability=SKILL_ID,
            status="validated", implementation_hash=IMPLEMENTATION_HASH,
            validation_json=evidence,
        ).on_conflict_do_nothing(index_elements=["skill_id", "version"])
    )
    existing = db.get(SkillVersion, (SKILL_ID, VERSION))
    if existing.implementation_hash != IMPLEMENTATION_HASH or existing.status != "validated" or existing.validation_json != evidence:
        raise ValueError("This version already has different code, status, or validation evidence. Create a new version instead of overwriting it.")
    return evidence


def main():
    if settings.app_env != "development":
        raise SystemExit("Registration requires APP_ENV=development.")
    try:
        with SessionLocal.begin() as db:
            evidence = register_skill(db)
        print(f"Registered {SKILL_ID} v{VERSION}: {evidence['test_count']} tests passed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
