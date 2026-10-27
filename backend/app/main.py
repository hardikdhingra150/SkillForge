import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.tasks import router as tasks_router
from app.api.inputs import router as inputs_router
from app.api.skills import router as skills_router
from app.config import settings
from app.database.connection import engine

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Idempotency-Key"],
)

app.include_router(tasks_router)
app.include_router(inputs_router)
app.include_router(skills_router)


@app.get("/api/v1/health/live")
async def health() -> dict[str, str]:
    return {
        "service": "skillforge",
        "api": "ready",
        "environment": settings.app_env,
    }


@app.get("/api/v1/health/ready")
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    except SQLAlchemyError as error:
        logger.warning(
            "Database readiness failed: %s",
            type(error).__name__,
        )

        raise HTTPException(
            status_code=503,
            detail={
                "code": "DATABASE_UNAVAILABLE",
                "message": "PostgreSQL connection failed.",
            },
        ) from None

    return {
        "service": "skillforge",
        "api": "ready",
        "database": "ready",
    }