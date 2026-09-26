"""
app/config.py
─────────────
Application-wide settings loaded from environment variables / .env file.
Uses pydantic-settings for type-safe configuration with validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime configuration values for StockSense."""

    # ── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/stocksense_db"
    )

    # ── JWT / Auth ───────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-very-long-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Seed defaults ────────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@stocksense.local"
    ADMIN_PASSWORD: str = "Admin@123"
    ADMIN_NAME: str = "System Administrator"

    # ── OTP policy ──────────────────────────────────────────────────────────
    OTP_EXPIRE_MINUTES: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_ATTEMPTS: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# Module-level singleton consumed everywhere via `from app.config import settings`
settings = Settings()
