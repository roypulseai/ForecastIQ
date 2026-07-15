"""Application configuration using Pydantic Settings."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _parse_list_env(value) -> List[str]:
    """Parse a list field from env. Accepts JSON array or comma-separated string."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return []
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                pass
        return [x.strip() for x in v.split(",") if x.strip()]
    return []


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "ForecastIQ"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"

    DATA_DIR: str = Field(
        default_factory=lambda: str(BACKEND_ROOT / "data"),
        description="Directory for persistent metadata + dataset storage",
    )
    UPLOAD_DIR: str = Field(
        default_factory=lambda: str(BACKEND_ROOT / "data" / "uploads"),
        description="Directory for raw uploaded files",
    )
    OUTPUT_DIR: str = Field(
        default_factory=lambda: str(BACKEND_ROOT / "data" / "outputs"),
        description="Directory for forecast result exports",
    )
    TEMPLATE_DIR: str = Field(
        default_factory=lambda: str(BACKEND_ROOT / "app" / "templates"),
        description="Directory for downloadable CSV templates",
    )

    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100 MB
    ALLOWED_EXTENSIONS: List[str] = [".csv", ".xlsx", ".xls", ".parquet"]

    # CORS: explicit origins. '*' is incompatible with credentials=True.
    # Pydantic Settings auto-parses list fields from JSON or comma-separated env values.
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8080",
        ]
    )

    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"

    REDIS_URL: str = Field(
        default="",
        description="Redis URL for persistent job queue. Empty = use in-memory queue.",
    )

    # ---- Public API ----
    # Whether the public /v1/* API is exposed. When false, the routes are
    # still registered but the auth dependency short-circuits. Useful for
    # self-hosted single-user installations that don't want API key
    # management. Defaults to enabled.
    PUBLIC_API_ENABLED: bool = True
    # Default tier for newly created API keys. Operators can override
    # this to "pro" or "enterprise" to give all keys more headroom.
    DEFAULT_API_KEY_TIER: str = "free"

    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: __import__("secrets").token_hex(32),
        description="Secret key for JWT tokens. Set in env for production.",
    )

    def ensure_dirs(self) -> None:
        """Create all required directories on startup."""
        for d in (self.DATA_DIR, self.UPLOAD_DIR, self.OUTPUT_DIR, self.TEMPLATE_DIR):
            os.makedirs(d, exist_ok=True)


settings = Settings()
# Defensive: if env var was delivered as raw string, normalize it.
if isinstance(settings.BACKEND_CORS_ORIGINS, str):
    settings.BACKEND_CORS_ORIGINS = _parse_list_env(settings.BACKEND_CORS_ORIGINS)
settings.ensure_dirs()
