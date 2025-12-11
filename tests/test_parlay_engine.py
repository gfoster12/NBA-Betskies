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
        team_tag=f"game_{idx}",
    )


def test_build_parlays_basic() -> None:
    legs = [_leg(1), _leg(2), _leg(3)]
    parlays = engine.build_parlays(legs, slate_date=date.today(), bankroll=1000, max_legs=2, edge_threshold=0.01)
    assert parlays
    assert parlays[0].hit_probability <= 1.0


def test_kelly_stake_positive() -> None:
    stake = engine.kelly_stake(prob=0.6, decimal_odds=2.5, bankroll=1000, fraction=0.25)
    assert stake > 0
