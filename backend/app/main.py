import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.activity import router as activity_router
from app.api.audit import router as audit_router
from app.api.browser import router as browser_router
from app.api.chat import fail_interrupted_turns
from app.api.chat import router as chat_router
from app.api.connector import device as connector_device_router
from app.api.connector import studio as connector_router
from app.api.inputs import router as inputs_router
from app.api.metrics import router as metrics_router
from app.api.review import router as review_router
from app.api.skills import router as skills_router
from app.api.tasks import router as tasks_router
from app.config import settings
from app.database.connection import engine
from app.database.session import SessionLocal
from app.rate_limit import rate_limit
from app.security import redact_access_logs

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    redact_access_logs()
    try:
        with SessionLocal.begin() as db:
            fail_interrupted_turns(db)
    except SQLAlchemyError as error:
        logger.warning("Could not reset interrupted chat replies: %s", getattr(error, "orig", error))
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.middleware("http")(rate_limit)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.include_router(browser_router)
app.include_router(connector_router)
app.include_router(connector_device_router)
app.include_router(tasks_router)
app.include_router(inputs_router)
app.include_router(skills_router)
app.include_router(activity_router)
app.include_router(chat_router)
app.include_router(review_router)
app.include_router(metrics_router)
app.include_router(audit_router)


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

STATUS_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>SkillForge API</title>
<style>
  :root {{ color-scheme: light dark; --bg: #f4f4f4; --fg: #161616; --muted: #5c5c5c; --line: #d6d6d6; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #141414; --fg: #ededed; --muted: #a3a3a3; --line: #333; }} }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; background: var(--bg); color: var(--fg);
         font: 16px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }}
  main {{ width: min(560px, calc(100vw - 32px)); padding: 28px; border: 1px solid var(--line); border-radius: 16px; }}
  h1 {{ margin: 0 0 6px; font-size: 24px; }}
  p {{ margin: 0 0 14px; color: var(--muted); }}
  ul {{ margin: 0; padding: 0; list-style: none; }}
  li {{ padding: 10px 0; border-top: 1px solid var(--line); }}
  a {{ color: var(--fg); font-weight: 600; }}
  .ok {{ display: inline-block; margin-bottom: 12px; padding: 2px 10px; border-radius: 99px; font-size: 13px;
         background: #1f7a3a; color: #fff; }}
</style>
</head>
<body>
<main>
  <span class="ok">Running</span>
  <h1>SkillForge API</h1>
  <p>This is SkillForge's backend. It has no pages for people: the web app talks to it at <code>/api/v1</code>.</p>
  <ul>
    {website}
    <li><a href="/api/v1/health/ready">Health check</a>: is the API up, and does the database answer?</li>
    <li><a href="/docs">API documentation</a>: every endpoint, for developers.</li>
  </ul>
</main>
</body>
</html>
"""


@app.get("/", include_in_schema=False)
def status_page():
    """What people see when they open the backend's address: it is running, and where to go instead."""
    from html import escape

    from fastapi.responses import HTMLResponse

    site = next((origin for origin in settings.frontend_origins if origin.startswith("https://")), None)
    website = (f'<li><a href="{escape(site, quote=True)}">Open SkillForge</a>: the website people use.</li>'
               if site else "")
    return HTMLResponse(STATUS_PAGE.format(website=website))
