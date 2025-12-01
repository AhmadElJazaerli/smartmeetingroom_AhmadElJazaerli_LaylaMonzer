"""Centralized application configuration using Pydantic settings."""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven configuration shared across services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="sqlite:///./smartmeeting.db",
        description="SQLAlchemy database URL. Defaults to local SQLite for development.",
    )
    run_db_migrations: bool = Field(
        default=False,
        description="Whether this service should create/update database tables on startup.",
    )
    jwt_secret: str = Field(default="super-secret", description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=60, description="Token lifetime in minutes")
    service_api_key: str = Field(default="service-key", description="API key for service-to-service calls")
    cors_origins: List[str] = Field(default_factory=lambda: ["*"], description="Allowed CORS origins")
    default_rate_limit: str = Field(default="30/minute", description="Global rate limiting rule")
    room_cache_ttl: int = Field(default=60, description="TTL (s) for cached room availability results")
    rate_limiting_enabled: bool = Field(default=True, description="Toggle to disable SlowAPI limits (useful in tests)")

    users_service_port: int = 8001
    rooms_service_port: int = 8002
    bookings_service_port: int = 8003
    reviews_service_port: int = 8004


@lru_cache
def get_settings() -> Settings:
    """Return a cached instance of the Settings object."""

    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached Settings instance (useful for tests)."""

    get_settings.cache_clear()
