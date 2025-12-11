"""Parlay engine tests."""

from __future__ import annotations

from datetime import date

from parlaylab.parlays import engine
from parlaylab.parlays.types import BetLeg


def _leg(idx: int, edge: float = 0.1) -> BetLeg:
    return BetLeg(
        bet_id=idx,
        market_type="spread",
        selection=f"Team {idx} -3.5",
        sportsbook="MockBook",
        american_odds=-110,
        implied_prob=0.524,
        model_prob=0.60,
        edge=edge,
        game_id=idx,
        team_id=idx,
    )


def _player_leg(bet_id: int, player_id: int) -> BetLeg:
    return BetLeg(
        bet_id=bet_id,
        market_type="player_points",
        selection=f"Player {player_id} over 25.5 pts",
        sportsbook="MockBook",
        american_odds=120,
        implied_prob=0.45,
        model_prob=0.58,
        edge=0.12,
        game_id=99,
        team_id=5,
        player_id=player_id,
    )


def test_build_parlays_basic() -> None:
    legs = [_leg(1), _leg(2), _leg(3)]
    parlays = engine.build_parlays(
        legs,
        slate_date=date.today(),
        bankroll=1000,
        max_legs=2,
        edge_threshold=0.01,
    )
    assert parlays
    assert parlays[0].hit_probability <= 1.0


def test_kelly_stake_positive() -> None:
    stake = engine.kelly_stake(prob=0.6, decimal_odds=2.5, bankroll=1000, fraction=0.25)
    assert stake > 0


def test_high_correlation_combo_filtered() -> None:
    legs = [_player_leg(1, 42), _player_leg(2, 42)]
    parlays = engine.build_parlays(
        legs,
        slate_date=date.today(),
        bankroll=1000,
        max_legs=2,
        edge_threshold=0.01,
    )
    assert not parlays
