"""
AEQUITAS — Application configuration.

All settings are read from environment variables (or .env file).
Import the `settings` singleton anywhere in the app:

    from app.config import settings
    print(settings.database_url)
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Typed application settings loaded from environment variables.

    pydantic-settings reads variables from:
      1. Environment variables (highest priority)
      2. .env file
      3. Default values defined here (lowest priority)

    This means the same code works locally (reads .env) and in
    production (reads real environment variables injected by Railway/Vercel).
    """

    model_config = SettingsConfigDict(
        env_file=["../.env", ".env"],  # ← look in parent dir first, then current
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    app_env: str = Field(default="development")
    app_debug: bool = Field(default=True)
    secret_key: str = Field(default="change-me-in-production")
    log_level: str = Field(default="INFO")

    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://aequitas:aequitas@localhost:5432/aequitas"
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── AI / LLM ──────────────────────────────────────────────
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-20250514")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")

    # ── Market data ───────────────────────────────────────────
    polygon_api_key: str = Field(default="")

    # ── Reddit ────────────────────────────────────────────────
    reddit_client_id: str = Field(default="")
    reddit_client_secret: str = Field(default="")
    reddit_user_agent: str = Field(default="aequitas-bot/1.0")

    # ── Auth ──────────────────────────────────────────────────
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)

    # ── CORS ──────────────────────────────────────────────────
    cors_origins: list[str] = Field(default=["http://localhost:3000"])

    # ── Computed properties ───────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def async_database_url(self) -> str:
        """
        SQLAlchemy needs asyncpg:// not postgresql:// for async connections.
        This property auto-converts so you never have to remember.
        """
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings singleton.
    Use get_settings.cache_clear() in tests to reset between runs.
    """
    return Settings()


settings = get_settings()
