"""Bring the database up to date, then serve the API, in one Python process.

On small hosts (Render's free plan has a tenth of a CPU) loading the app is the slow part of starting, and these
hosts start again every time they wake up, so doing it once instead of twice gets the site answering sooner.

If the database can't be reached (a free Supabase project paused itself, a network blip), the API still starts:
its health check says the database is unavailable, the website says the server is starting, and the migration is
retried in the background until it succeeds. Before, the process exited and the host restarted it in a loop.
"""

import logging
import os
import threading
import time
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]
RETRY_SECONDS = 30
logger = logging.getLogger("skillforge.serve")


def migrate() -> bool:
    try:
        command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")
        return True
    except Exception as error:  # any database or connection failure: report it and keep serving
        message = str(getattr(error, "orig", error)).strip().splitlines()
        logger.error("Database migration failed (will retry every %ds): %s", RETRY_SECONDS,
                     message[0][:300] if message else type(error).__name__)
        return False


def keep_migrating(sleep=time.sleep):
    """Retry until the database is reachable and up to date."""
    while not migrate():
        sleep(RETRY_SECONDS)
    logger.warning("Database is reachable again and up to date.")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not migrate():
        threading.Thread(target=keep_migrating, name="migrate-retry", daemon=True).start()

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), proxy_headers=True,
                forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"))


if __name__ == "__main__":
    main()
