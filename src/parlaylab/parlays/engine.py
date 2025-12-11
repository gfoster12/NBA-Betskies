"""Parlay construction logic."""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from datetime import date

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


def pairwise_correlation(a: BetLeg, b: BetLeg) -> float:
    score = 0.0
    if a.game_id == b.game_id:
        score += 0.4
    if a.team_id and b.team_id and a.team_id == b.team_id:
        score += 0.25
    if a.player_id and b.player_id and a.player_id == b.player_id:
        score += 0.5
    if a.market_type == b.market_type and a.game_id == b.game_id:
        score += 0.1
    return min(score, 1.0)


def combination_correlation_score(legs: list[BetLeg]) -> float:
    score = 0.0
    for leg_a, leg_b in itertools.combinations(legs, 2):
        score += pairwise_correlation(leg_a, leg_b)
    return score


def apply_correlation_penalty(prob: float, corr_score: float) -> float:
    penalty = min(corr_score * settings.correlation_penalty_weight, 0.9)
    return max(prob * (1 - penalty), 0.0)


def build_parlays(
    bets: Iterable[BetLeg],
    slate_date: date,
    bankroll: float,
    max_legs: int = 3,
    top_n_bets: int = 12,
    kelly_fraction: float = settings.kelly_fraction,
    edge_threshold: float = settings.edge_threshold,
) -> list[ParlayRecommendation]:
    """Generate ranked parlay recommendations."""

    filtered = [bet for bet in bets if bet.edge >= edge_threshold]
    filtered.sort(key=lambda b: b.edge, reverse=True)
    filtered = filtered[:top_n_bets]

    parlays: list[ParlayRecommendation] = []
    for r in range(2, max_legs + 1):
        for combo in itertools.combinations(filtered, r):
            legs = list(combo)
            corr_score = combination_correlation_score(legs)
            if corr_score > settings.max_correlation_score:
                continue
            base_prob = parlay_probability(legs)
            prob = apply_correlation_penalty(base_prob, corr_score)
            if prob <= 0:
                continue
            decimal_odds = combine_odds(legs)
            stake = max(kelly_stake(prob, decimal_odds, bankroll, kelly_fraction), 5.0)
            ev = expected_value(prob, decimal_odds, stake)
            parlays.append(
                ParlayRecommendation(
                    name=f"{r}-Leg Parlay",
                    slate_date=slate_date,
                    legs=legs,
                    total_odds=decimal_odds,
                    hit_probability=prob,
                    expected_value=ev,
                    suggested_stake=stake,
                    tags={"base_prob": f"{base_prob:.3f}"},
                    correlation_score=corr_score,
                )
            )
    parlays.sort(key=lambda p: (p.expected_value, p.hit_probability), reverse=True)
    return parlays


def flagship_and_alternatives(
    parlays: list[ParlayRecommendation],
) -> tuple[ParlayRecommendation | None, list[ParlayRecommendation]]:
    if not parlays:
        return None, []
    flagship = parlays[0]
    return flagship, parlays[1:4]
