"""Parlay construction logic."""

from __future__ import annotations

import itertools
from datetime import date
from typing import Iterable, List

from parlaylab.config import get_settings
from parlaylab.parlays.types import BetLeg, ParlayRecommendation


settings = get_settings()


def american_to_decimal(odds: int) -> float:
    return 1 + (odds / 100) if odds > 0 else 1 + (100 / abs(odds))


def combine_odds(legs: Iterable[BetLeg]) -> float:
    decimal = 1.0
    for leg in legs:
        decimal *= american_to_decimal(leg.american_odds)
    return decimal


def parlay_probability(legs: Iterable[BetLeg]) -> float:
    prob = 1.0
    for leg in legs:
        prob *= leg.model_prob
    return prob


def expected_value(prob: float, decimal_odds: float, stake: float) -> float:
    payout = stake * (decimal_odds - 1)
    return prob * payout - (1 - prob) * stake


def kelly_stake(prob: float, decimal_odds: float, bankroll: float, fraction: float) -> float:
    b = decimal_odds - 1
    edge = (prob * (b + 1) - 1) / b if b else 0
    kelly = max(edge / b, 0)
    return bankroll * kelly * fraction


def correlation_safe(legs: List[BetLeg]) -> bool:
    seen_games: set[int] = set()
    seen_players: set[str] = set()
    for leg in legs:
        if leg.game_id in seen_games:
            return False
        seen_games.add(leg.game_id)
        if leg.player_tag:
            if leg.player_tag in seen_players:
                return False
            seen_players.add(leg.player_tag)
    return True


def build_parlays(
    bets: Iterable[BetLeg],
    slate_date: date,
    bankroll: float,
    max_legs: int = 3,
    top_n_bets: int = 12,
    kelly_fraction: float = settings.kelly_fraction,
    edge_threshold: float = settings.edge_threshold,
) -> List[ParlayRecommendation]:
    """Generate ranked parlay recommendations."""

    filtered = [bet for bet in bets if bet.edge >= edge_threshold]
    filtered.sort(key=lambda b: b.edge, reverse=True)
    filtered = filtered[:top_n_bets]

    parlays: List[ParlayRecommendation] = []
    for r in range(2, max_legs + 1):
        for combo in itertools.combinations(filtered, r):
            if not correlation_safe(list(combo)):
                continue
            prob = parlay_probability(combo)
            decimal_odds = combine_odds(combo)
            stake = max(kelly_stake(prob, decimal_odds, bankroll, kelly_fraction), 5.0)
            ev = expected_value(prob, decimal_odds, stake)
            parlays.append(
                ParlayRecommendation(
                    name=f"{r}-Leg Parlay",
                    slate_date=slate_date,
                    legs=list(combo),
                    total_odds=decimal_odds,
                    hit_probability=prob,
                    expected_value=ev,
                    suggested_stake=stake,
                )
            )
    parlays.sort(key=lambda p: (p.expected_value, p.hit_probability), reverse=True)
    return parlays


def flagship_and_alternatives(parlays: List[ParlayRecommendation]) -> tuple[ParlayRecommendation | None, List[ParlayRecommendation]]:
    if not parlays:
        return None, []
    flagship = parlays[0]
    return flagship, parlays[1:4]
