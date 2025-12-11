"""Tests for marketing agent LLM abstraction."""

from __future__ import annotations

from datetime import date

from parlaylab.agents import marketing_agent as ma
from parlaylab.parlays.types import BetLeg, ParlayRecommendation


def _parlay() -> ParlayRecommendation:
    leg = BetLeg(
        bet_id=1,
        market_type="moneyline",
        selection="Sample Team ML",
        sportsbook="MockBook",
        american_odds=120,
        implied_prob=0.45,
        model_prob=0.55,
        edge=0.10,
        game_id=101,
        team_id=101,
    )
    return ParlayRecommendation(
        name="Test Parlay",
        slate_date=date.today(),
        legs=[leg],
        total_odds=2.2,
        hit_probability=0.55,
        expected_value=12.5,
        suggested_stake=25.0,
    )


def test_marketing_agent_generates_two_tones(monkeypatch) -> None:
    monkeypatch.setattr(ma, "generate_ig_caption", lambda parlay, stats, tone: f"{tone}-caption")
    agent = ma.MarketingAgent()
    content = agent.run(_parlay(), {"roi": "+5%"})
    assert "professional" in content.professional
    assert "fun" in content.hype
    assert "#" in content.hashtags
