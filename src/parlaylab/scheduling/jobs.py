"""Scheduling entry points."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List

from sqlalchemy import select

from parlaylab.agents.llm_client import explain_parlay
from parlaylab.agents.marketing_agent import MarketingAgent
from parlaylab.config import get_settings
from parlaylab.data.ingestion import fetch_edges, sync_daily
from parlaylab.db.database import get_session
from parlaylab.db.models import Bet, Parlay as ParlayModel, ParlayLeg as ParlayLegModel, Subscriber
from parlaylab.notifications.service import NotificationService
from parlaylab.parlays.engine import build_parlays, flagship_and_alternatives
from parlaylab.parlays.types import BetLeg, ParlayRecommendation

settings = get_settings()


def _bet_to_leg(bet: Bet) -> BetLeg:
    return BetLeg(
        bet_id=bet.id,
        market_type=bet.market_type,
        selection=bet.selection,
        sportsbook=bet.sportsbook,
        american_odds=bet.american_odds,
        implied_prob=bet.implied_prob,
        model_prob=bet.model_prob,
        edge=bet.edge,
        game_id=bet.game_id,
        team_tag=f"game_{bet.game_id}",
        player_tag=None,
    )


def _persist_parlay(rec: ParlayRecommendation) -> None:
    with get_session() as session:
        parlay = ParlayModel(
            name=rec.name,
            slate_date=rec.slate_date,
            total_odds=rec.total_odds,
            hit_probability=rec.hit_probability,
            expected_value=rec.expected_value,
            suggested_stake=rec.suggested_stake,
            flagship=True,
            rationale=rec.rationale,
        )
        session.add(parlay)
        session.flush()
        for order, leg in enumerate(rec.legs):
            leg_model = ParlayLegModel(parlay_id=parlay.id, bet_id=leg.bet_id, leg_order=order)
            session.add(leg_model)


def _load_subscribers() -> List[Dict[str, str]]:
    with get_session() as session:
        stmt = select(Subscriber).where(Subscriber.active.is_(True))
        subscribers = [
            {
                "email": sub.email,
                "phone": sub.phone,
                "name": sub.name or "Subscriber",
                "bankroll": float(sub.bankroll_pref or settings.default_bankroll),
            }
            for sub in session.scalars(stmt)
        ]
    return subscribers


def run_daily_job(target_date: date | None = None) -> Dict[str, int]:
    """Run the full daily workflow: ingest -> recommend -> notify."""

    target_date = target_date or date.today()
    sync_result = sync_daily(target_date)
    bet_legs = [_bet_to_leg(bet) for bet in fetch_edges(settings.edge_threshold)]
    parlays = build_parlays(
        bet_legs,
        slate_date=target_date,
        bankroll=settings.default_bankroll,
        max_legs=4,
        kelly_fraction=settings.kelly_fraction,
        edge_threshold=settings.edge_threshold,
    )
    flagship, alternatives = flagship_and_alternatives(parlays)

    if flagship:
        stats = {"generated_at": datetime.utcnow().isoformat()}
        flagship.rationale = explain_parlay(flagship, stats)
        _persist_parlay(flagship)
        subscribers = _load_subscribers()
        NotificationService().notify_subscribers(flagship, subscribers)
        MarketingAgent().run(flagship, stats)

    return {
        "games": sync_result["games"],
        "bets": sync_result["bets"],
        "parlays": len(parlays),
        "alternatives": len(alternatives),
    }


def main() -> None:  # pragma: no cover - CLI convenience
    run_daily_job()


if __name__ == "__main__":  # pragma: no cover
    main()
