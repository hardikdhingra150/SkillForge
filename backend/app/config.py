from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    app_name: str = "SkillForge API"
    app_env: Literal["development", "production"] = "development"

    frontend_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "skillforge"
    postgres_user: str = "skillforge"
    postgres_password: SecretStr | None = None

    # Or one connection string, e.g. Supabase's "Session pooler" URI. When set it replaces the POSTGRES_* values
    # above (POSTGRES_PASSWORD may then be left out).
    database_url: SecretStr | None = None

    # browser: no sign-in; every browser silently gets its own private workspace for tasks, chats, reviews and
    # history (the skill library stays shared). off: one shared workspace. .env.example and compose.yaml turn
    # browser on; the code default stays off so tools and tests see the shared workspace.
    auth_mode: Literal["off", "browser"] = "off"

    # Bearer token for /api/v1 (generate with `make token`). Unset: open in development, closed in production.
    api_token: SecretStr | None = Field(default=None, min_length=32)

    # Where skills run: "process" (a locked-down child process) or "docker" (a throwaway container with no
    # network, a read-only filesystem, no capabilities and memory/PID limits). Production requires docker.
    sandbox_backend: Literal["process", "docker"] = "process"
    sandbox_image: str = "python:3.14-slim"
    # True when SANDBOX_IMAGE already holds the sandbox code (backend/docker/sandbox.Dockerfile). Needed when the
    # API and worker run in containers themselves: the host's Docker can't mount files from inside them.
    sandbox_code_in_image: bool = False
    # Hosts that can't start containers (Hugging Face Spaces, Render, Railway) can only use the process sandbox:
    # code is checked before it runs, network, file and process access are blocked, CPU and memory are limited,
    # and it gets no environment variables. That is weaker isolation than a container. Production refuses it
    # unless this is set, as a deliberate choice.
    allow_process_sandbox: bool = False
    # How long one skill run may take (wall clock). Its CPU time is capped one second past this as well. Raise it
    # on hosts with a small slice of a CPU (Render's free plan), where starting the sandboxed process alone is slow.
    sandbox_timeout_seconds: float = Field(default=10.0, ge=1, le=300)

    # Requests per client per minute on /api/v1 (health checks are exempt).
    rate_limit_writes_per_minute: int = Field(default=60, ge=1)
    rate_limit_reads_per_minute: int = Field(default=600, ge=1)

    # Model budget: agent chat replies per workspace per 24 hours (each reply may make several model calls).
    chat_turns_per_day: int = Field(default=200, ge=1)
    # And across every visitor's workspace together, so opening new browsers can't get around the limit above.
    # The owner (API_TOKEN, or AUTH_MODE=off) is not counted.
    chat_turns_per_day_total: int = Field(default=500, ge=1)
    # Models visitors may use in browser mode. The Claude Code and Codex CLIs run on the owner's own logins,
    # so by default only the owner can use them; visitors get Groq's free hosted models and the local model.
    public_providers: list[str] = Field(default_factory=lambda: ["groq", "ollama"])
    # Browser mode: delete a visitor's workspace after this many days without a visit, task or chat (0: never).
    workspace_retention_days: int = Field(default=30, ge=0)

    # How many repair strategies the worker may try before asking a person to review.
    repair_budget: int = Field(default=2, ge=0, le=5)

    @field_validator("database_url", mode="before")
    @classmethod
    def blank_means_unset(cls, value):
        return value or None

    @model_validator(mode="after")
    def has_a_database(self):
        if self.database_url is None and self.postgres_password is None:
            raise ValueError("Set DATABASE_URL or POSTGRES_PASSWORD in backend/.env (see backend/.env.example).")
        return self

    def database_password(self) -> str:
        if self.database_url is not None:
            from sqlalchemy import make_url

            return make_url(self.database_url.get_secret_value()).password or ""
        return self.postgres_password.get_secret_value()

    @model_validator(mode="after")
    def production_is_locked_down(self):
        """Refuse to start in production with settings that are only safe on a laptop."""
        if self.app_env != "production":
            return self
        problems = []
        if self.api_token is None and self.auth_mode != "browser":
            problems.append("Set AUTH_MODE=browser or API_TOKEN (make token).")
        if self.sandbox_backend != "docker" and not self.allow_process_sandbox:
            problems.append("SANDBOX_BACKEND must be docker, or set ALLOW_PROCESS_SANDBOX=true on a host that "
                            "can't run containers (see DEPLOY.md).")
        if not self.frontend_origins:
            problems.append("FRONTEND_ORIGINS must list the site's origin.")
        for origin in self.frontend_origins:
            if origin == "*" or not origin.startswith("https://"):
                problems.append(f"FRONTEND_ORIGINS entries must be https:// origins, not {origin!r}.")
        password = self.database_password()
        if len(password) < 16 or password in {"change-me", "skillforge", "postgres", "password"}:
            problems.append("POSTGRES_PASSWORD must be a strong, non-default password (16+ characters).")
        if problems:
            raise ValueError("Unsafe production settings: " + " ".join(problems))
        return self

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_DIR / ".env.postgres",
            BACKEND_DIR / ".env",
        ),
        env_file_encoding="utf-8",
        extra="forbid",
    )


settings = Settings()