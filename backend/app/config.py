from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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
    postgres_password: SecretStr

    # Bearer token for /api/v1 (generate with `make token`). Unset: open in development, closed in production.
    api_token: SecretStr | None = Field(default=None, min_length=32)

    # Where skills run: "process" (a locked-down child process) or "docker" (a throwaway container with no
    # network, a read-only filesystem, no capabilities and memory/PID limits). Production requires docker.
    sandbox_backend: Literal["process", "docker"] = "process"
    sandbox_image: str = "python:3.14-slim"

    # How many repair strategies the worker may try before asking a person to review.
    repair_budget: int = Field(default=2, ge=0, le=5)

    @model_validator(mode="after")
    def production_is_locked_down(self):
        """Refuse to start in production with settings that are only safe on a laptop."""
        if self.app_env != "production":
            return self
        problems = []
        if self.api_token is None:
            problems.append("API_TOKEN is required (make token).")
        if self.sandbox_backend != "docker":
            problems.append("SANDBOX_BACKEND must be docker.")
        if not self.frontend_origins:
            problems.append("FRONTEND_ORIGINS must list the site's origin.")
        for origin in self.frontend_origins:
            if origin == "*" or not origin.startswith("https://"):
                problems.append(f"FRONTEND_ORIGINS entries must be https:// origins, not {origin!r}.")
        password = self.postgres_password.get_secret_value()
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