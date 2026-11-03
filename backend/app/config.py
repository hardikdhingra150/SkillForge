from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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

    # How many repair strategies the worker may try before asking a person to review.
    repair_budget: int = Field(default=2, ge=0, le=5)

    # Optional API-key providers (for deployment). Never sent to the browser or stored in the database.
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5"

    model_config = SettingsConfigDict(
        env_file=(
            PROJECT_DIR / ".env.postgres",
            BACKEND_DIR / ".env",
        ),
        env_file_encoding="utf-8",
        extra="forbid",
    )


settings = Settings()