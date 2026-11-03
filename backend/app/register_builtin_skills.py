from app.config import settings
from app.database.connection import engine
from app.database.session import SessionLocal
from app.services.skill_registry import register_builtin
from app.skills import BUILTIN_SKILLS


def main():
    if settings.app_env != "development":
        raise SystemExit("Registration requires APP_ENV=development.")
    try:
        with SessionLocal.begin() as db:
            for skill in BUILTIN_SKILLS:
                evidence = register_builtin(db, skill)
                print(f"Registered {skill.skill_id} v{skill.version}: {evidence['test_count']} sandbox tests passed.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
