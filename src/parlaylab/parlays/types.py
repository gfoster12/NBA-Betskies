"""Dataclasses for bet and parlay modeling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List


@dataclass
class BetLeg:
    bet_id: int
    market_type: str
    selection: str
    sportsbook: str
    american_odds: int
    implied_prob: float
    model_prob: float
    edge: float
    game_id: int
    team_tag: str
    player_tag: str | None = None


@dataclass
class ParlayRecommendation:
    name: str
    slate_date: date
    legs: List[BetLeg]
    total_odds: float
    hit_probability: float
    expected_value: float
    suggested_stake: float
    rationale: str = ""
    tags: dict[str, str] = field(default_factory=dict)
