"""Application configuration using Pydantic settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    pythonpath: Path = Field(default=Path.cwd())
    database_url: AnyUrl | str = Field(default="sqlite:///./parlaylab.db")

    balldontlie_api_key: str = Field(default="", validation_alias="BALLDONTLIE_API_KEY")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.1-pro", validation_alias="OPENAI_MODEL")

    email_host: str = Field(default="smtp.example.com")
    email_port: int = Field(default=587)
    email_user: Optional[str] = None
    email_password: Optional[str] = None
    email_from: str = Field(default="alerts@parlaylab.nba")

    admin_password: str = Field(default="change_me")

    default_bankroll: float = Field(default=1000.0)
    kelly_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    edge_threshold: float = Field(default=0.05, ge=-1.0, le=1.0)
    scheduler_run_hour: int = Field(default=9, ge=0, le=23)

    slack_webhook_url: Optional[str] = None
    notification_mode: Literal["email", "sms", "both"] = "email"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()  # type: ignore[call-arg]
