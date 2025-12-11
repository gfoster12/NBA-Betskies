"""Pydantic schemas for BallDontLie responses and internal data."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class TeamSchema(BaseModel):
    id: int
    abbreviation: str
    city: str
    conference: str
    division: str
    full_name: str
    name: str


class PlayerSchema(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str
    team: TeamSchema


class GameSchema(BaseModel):
    id: int
    date: datetime
    season: int
    status: str
    home_team: TeamSchema
    visitor_team: TeamSchema


class InjurySchema(BaseModel):
    player_id: int
    description: str | None
    status: str | None
    last_updated: datetime | None


class OddsLegSchema(BaseModel):
    market_type: str
    selection: str
    american_odds: int
    sportsbook: str

    def implied_probability(self) -> float:
        """Convert American odds into implied probability."""

        odds = self.american_odds
        if odds > 0:
            return 100.0 / (odds + 100.0)
        return -odds / (-odds + 100.0)


class BettingOddsSchema(BaseModel):
    game_id: int
    date: date
    legs: list[OddsLegSchema]


class RollingFeatureSet(BaseModel):
    """Feature set for team/player modeling."""

    entity_id: int
    entity_type: str = Field(description="team or player")
    features: dict[str, float]
    as_of: date
