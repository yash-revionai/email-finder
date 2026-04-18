from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env", PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Email Finder API"
    debug: bool = False
    database_echo: bool = False
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/email_finder"
    redis_url: str = "redis://localhost:6379/0"
    exa_api_key: str | None = None
    exa_base_url: str = "https://api.exa.ai"
    exa_timeout_seconds: float = 30.0
    firecrawl_api_key: str | None = None
    firecrawl_base_url: str = "https://api.firecrawl.dev/v2"
    firecrawl_timeout_seconds: float = 60.0
    omniverifier_api_key: str | None = None
    omniverifier_base_url: str = "https://api.omniverifier.com"
    omniverifier_validate_path: str = "/v1/validate/email/check"
    omniverifier_timeout_seconds: float = 30.0
    app_password: str | None = None
    jwt_secret: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> Any:
        if isinstance(value, bool) or value is None:
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "development", "dev"}:
                return True
            if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production"}:
                return False

        return value

    @field_validator(
        "exa_api_key",
        "firecrawl_api_key",
        "omniverifier_api_key",
        "app_password",
        "jwt_secret",
        mode="before",
    )
    @classmethod
    def empty_string_to_none(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("exa_base_url", "firecrawl_base_url", "omniverifier_base_url", mode="before")
    @classmethod
    def normalize_base_url(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.rstrip("/")
        return value

    @field_validator("omniverifier_validate_path", mode="before")
    @classmethod
    def normalize_api_path(cls, value: Any) -> Any:
        if isinstance(value, str) and value:
            stripped = value.strip()
            if not stripped.startswith("/"):
                return f"/{stripped}"
            return stripped
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
