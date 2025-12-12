"""ORM models for ParlayLab NBA."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarative class."""


class Game(Base):
    """NBA game metadata."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    away_team_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(64), default="scheduled")

    bets: Mapped[list[Bet]] = relationship(back_populates="game", cascade="all, delete-orphan")


class Bet(Base):
    """Represents a single-leg wager opportunity."""

    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    market_type: Mapped[str] = mapped_column(String(64), nullable=False)
    selection: Mapped[str] = mapped_column(String(255), nullable=False)
    team_id: Mapped[int | None] = mapped_column(Integer)
    player_id: Mapped[int | None] = mapped_column(Integer)
    sportsbook: Mapped[str] = mapped_column(String(64), nullable=False)
    american_odds: Mapped[int] = mapped_column(Integer, nullable=False)
    implied_prob: Mapped[float] = mapped_column(Float, nullable=False)
    model_prob: Mapped[float] = mapped_column(Float, nullable=False)
    edge: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    game: Mapped[Game] = relationship(back_populates="bets")
    parlay_legs: Mapped[list[ParlayLeg]] = relationship(back_populates="bet")


class Parlay(Base):
    """Parlay entity with aggregated stats."""

    __tablename__ = "parlays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    slate_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_odds: Mapped[float] = mapped_column(Float, nullable=False)
    hit_probability: Mapped[float] = mapped_column(Float, nullable=False)
    expected_value: Mapped[float] = mapped_column(Float, nullable=False)
    suggested_stake: Mapped[float] = mapped_column(Float, nullable=False)
    flagship: Mapped[bool] = mapped_column(Boolean, default=False)
    rationale: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    legs: Mapped[list[ParlayLeg]] = relationship(
        back_populates="parlay",
        cascade="all, delete-orphan",
    )


class ParlayLeg(Base):
    """Join table between parlays and bets."""

    __tablename__ = "parlay_legs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parlay_id: Mapped[int] = mapped_column(ForeignKey("parlays.id"), nullable=False)
    bet_id: Mapped[int] = mapped_column(ForeignKey("bets.id"), nullable=False)
    leg_order: Mapped[int] = mapped_column(Integer, default=0)

    parlay: Mapped[Parlay] = relationship(back_populates="legs")
    bet: Mapped[Bet] = relationship(back_populates="parlay_legs")


class Subscriber(Base):
    """Subscriber info retained for future outbound channels."""

    __tablename__ = "subscribers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    bankroll_pref: Mapped[float | None] = mapped_column(Numeric(10, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelRun(Base):
    """Track trained models and metrics."""

    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    artifact_path: Mapped[str] = mapped_column(String(255), nullable=False)
