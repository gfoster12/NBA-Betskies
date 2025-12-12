"""Pydantic schemas for the ParlayLab API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class ParlayLeg(BaseModel):
    market_type: str
    description: str
    odds: float | str
    model_prob: float
    implied_prob: float
    edge: float
    metadata: dict[str, Any] = Field(default_factory=dict)


class ParlayResponse(BaseModel):
    slate_date: date
    name: str
    legs: list[ParlayLeg]
    total_odds: float | str
    hit_probability: float
    expected_value: float
    suggested_stake: float
    flagship: bool = True
    created_at: datetime
    model_version: str | None = None


class StatsResponse(BaseModel):
    window_days: int
    total_parlays: int
    wins: int
    losses: int
    pushes: int
    win_rate: float
    roi: float
    avg_ev: float
    last_updated: datetime
