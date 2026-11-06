"""Bring the database up to date, then serve the API, in one Python process.

On small hosts (Render's free plan has a tenth of a CPU) loading the app is the slow part of starting, and these
hosts start again every time they wake up, so doing it once instead of twice gets the site answering sooner.
"""

import os
from pathlib import Path

from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[1]


def main():
    command.upgrade(Config(str(BACKEND / "alembic.ini")), "head")

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), proxy_headers=True,
                forwarded_allow_ips=os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1"))


if __name__ == "__main__":
    main()
