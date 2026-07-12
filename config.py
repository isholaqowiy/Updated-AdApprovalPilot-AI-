"""
Configuration module for AdApprovalPilot AI.
Loads and validates all required environment variables at process start.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_id: int
    admin_handle: str
    database_url: str
    gemini_api_key: str
    gemini_model: str
    free_daily_scan_limit: int
    environment: str


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {key}")
    return value


def load_settings() -> Settings:
    raw_db_url = _require("DATABASE_URL")
    if raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw_db_url.startswith("postgresql://"):
        raw_db_url = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return Settings(
        bot_token=_require("BOT_TOKEN"),
        admin_id=int(_require("ADMIN_ID")),
        admin_handle=os.getenv("ADMIN_HANDLE", "@BlockSavvyMx"),
        database_url=raw_db_url,
        gemini_api_key=_require("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        free_daily_scan_limit=int(os.getenv("FREE_DAILY_SCAN_LIMIT", "1")),
        environment=os.getenv("ENVIRONMENT", "production"),
    )


settings = load_settings()
