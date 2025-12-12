"""Environment-driven configuration helpers for ParlayLab NBA."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables or .env files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    pythonpath: Path = Field(default=Path.cwd())
    database_url: AnyUrl | str = Field(default="sqlite:///./parlaylab.db")

    balldontlie_api_key: str = Field(default="", validation_alias="BALLDONTLIE_API_KEY")

    admin_password: str = Field(default="change_me")

    default_bankroll: float = Field(default=1000.0)
    kelly_fraction: float = Field(default=0.25, ge=0.0, le=1.0)
    edge_threshold: float = Field(default=0.05, ge=-1.0, le=1.0)
    max_correlation_score: float = Field(default=0.8, ge=0.0, le=5.0)
    correlation_penalty_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    scheduler_run_hour: int = Field(default=9, ge=0, le=23)

    parlaylab_api_key: str = Field(default="", validation_alias="PARLAYLAB_API_KEY")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()  # type: ignore[call-arg]


def get_balldontlie_api_key() -> str:
    """Return the BALLDONTLIE API key or raise a helpful error."""

    key = os.getenv("BALLDONTLIE_API_KEY") or get_settings().balldontlie_api_key
    if not key:
        raise RuntimeError(
            "BALLDONTLIE_API_KEY is not configured. "
            "Set it in .env for local dev or as a GitHub secret."
        )
    return key


def get_api_access_key() -> str:
    key = os.getenv("PARLAYLAB_API_KEY") or get_settings().parlaylab_api_key
    if not key:
        raise RuntimeError(
            "PARLAYLAB_API_KEY is not configured. Set it in your environment or GitHub secrets."
        )
    return key
