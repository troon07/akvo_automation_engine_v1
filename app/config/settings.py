from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = Field(default="Automation Engine")
    environment: Literal["local", "development", "staging", "production"] = Field(
        default="local"
    )
    log_level: str = Field(default="INFO")

    supabase_url: str | None = Field(default=None)
    supabase_key: str | None = Field(default=None)

    scheduler_timezone: str = Field(default="UTC")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
