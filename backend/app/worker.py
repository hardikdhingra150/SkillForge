"""Run separately from Uvicorn: python -m app.worker."""

import argparse
import logging
import signal
import threading

from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database.connection import engine
from app.database.session import SessionLocal
from app.services.request_queue import review_next
from app.services.execution_queue import execute_next

logger = logging.getLogger("skillforge.worker")


def log_database_error(error: SQLAlchemyError) -> None:
    original = getattr(error, "orig", error)
    diagnostic = getattr(original, "diag", None)
    reason = getattr(diagnostic, "message_primary", None) or str(original)
    logger.error(
        "Worker database operation failed: %s; SQLSTATE=%s; reason=%s",
        type(original).__name__,
        getattr(original, "sqlstate", None),
        reason,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="SkillForge local worker")
    parser.add_argument("--once", action="store_true", help="Process at most one eligible queued task and exit")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    if not 0.5 <= args.poll_seconds <= 60:
        parser.error("--poll-seconds must be between 0.5 and 60")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if settings.app_env != "development":
        logger.error("This local worker requires APP_ENV=development.")
        return 2

    stop = threading.Event()

    def request_stop(_signal, _frame):
        stop.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    logger.info("Worker ready. Reviewing requests and executing confirmed sales tasks.")

    try:
        while not stop.is_set():
            try:
                # The current review is short and entirely local. A crash before
                # commit rolls everything back, leaving the task queued.
                with SessionLocal.begin() as db:
                    execution_id = review_next(db)
                    if execution_id is None:
                        execution_id = execute_next(db)
            except SQLAlchemyError as error:
                log_database_error(error)
                if args.once:
                    return 1
                stop.wait(5)
                continue
            except Exception:
                logger.exception("Worker transaction failed and was rolled back.")
                return 1

            if execution_id is not None:
                logger.info("Processed execution %s.", execution_id)
            elif args.once:
                logger.info("No eligible queued request is available.")

            if args.once:
                return 0
            if execution_id is None:
                stop.wait(args.poll_seconds)
    finally:
        engine.dispose()
        logger.info("Worker stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
