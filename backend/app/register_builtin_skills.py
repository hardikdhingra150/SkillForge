from app.database.connection import engine
from app.database.session import SessionLocal
from app.services.skill_registry import register_builtin
from app.skills import BUILTIN_SKILLS


def main():
    # Safe in every environment: built-in versions are only added, never overwritten (register_builtin refuses
    # if a stored version differs), and each must pass its tests in the configured sandbox first.
    try:
        with SessionLocal.begin() as db:
            for skill in BUILTIN_SKILLS:
                evidence = register_builtin(db, skill)
                if evidence.get("skipped"):
                    print(f"Skipped {skill.skill_id} v{skill.version}: {evidence['skipped']}.")
                else:
                    print(f"Registered {skill.skill_id} v{skill.version}: {evidence['test_count']} sandbox tests passed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
