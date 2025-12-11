"""Data ingestion utilities for ParlayLab."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Iterable

from sqlalchemy import select

from parlaylab.data.balldontlie_client import BallDontLieClient
from parlaylab.db.database import get_session
from parlaylab.db.models import Bet, Game


def american_to_implied(odds: int) -> float:
    """Convert American odds to implied probability."""

    if odds > 0:
        return 100 / (odds + 100)
    return -odds / (-odds + 100)


def sync_historical_data(start_season: int, end_season: int) -> int:
    """Load historical games between the provided seasons (inclusive)."""

    inserted = 0
    with BallDontLieClient() as client, get_session() as session:
        for season in range(start_season, end_season + 1):
            # naive approach: iterate through full season schedule
            season_start = date(season, 10, 1)
            season_end = date(season + 1, 6, 30)
            current = season_start
            while current <= season_end:
                for payload in client.get_games(current):
                    game = session.get(Game, payload["id"]) or Game(id=payload["id"])
                    game.season = payload["season"]
                    game.date = datetime.fromisoformat(payload["date"].replace("Z", "+00:00")).date()
                    game.status = payload.get("status", "scheduled")
                    game.home_team_id = payload["home_team"]["id"]
                    game.away_team_id = payload["visitor_team"]["id"]
                    game.home_score = payload.get("home_team_score")
                    game.away_score = payload.get("visitor_team_score")
                    session.add(game)
                    inserted += 1
                current += timedelta(days=1)
    return inserted


def _upsert_bet(session, game_id: int, data: dict) -> Bet:
    market = data.get("market_type", "unknown")
    selection = data.get("selection", "line")
    american_odds = int(data.get("american_odds", 100))
    edge = data.get("edge", 0.0)
    team_id = data.get("team_id") or (data.get("team") or {}).get("id")
    player_id = data.get("player_id") or (data.get("player") or {}).get("id")
    bet = Bet(
        game_id=game_id,
        market_type=market,
        selection=selection,
        team_id=team_id,
        player_id=player_id,
        sportsbook=data.get("sportsbook", "unknown"),
        american_odds=american_odds,
        implied_prob=american_to_implied(american_odds),
        model_prob=data.get("model_prob", 0.5),
        edge=edge,
    )
    session.add(bet)
    return bet


def sync_daily(target_date: date) -> dict:
    """Fetch today's games, odds, and create bet candidates."""

    summary = {"games": 0, "bets": 0}
    with BallDontLieClient() as client, get_session() as session:
        games = list(client.get_games(target_date))
        for payload in games:
            game = session.get(Game, payload["id"]) or Game(id=payload["id"])
            game.season = payload["season"]
            game.date = datetime.fromisoformat(payload["date"].replace("Z", "+00:00")).date()
            game.status = payload.get("status", "scheduled")
            game.home_team_id = payload["home_team"]["id"]
            game.away_team_id = payload["visitor_team"]["id"]
            game.home_score = payload.get("home_team_score")
            game.away_score = payload.get("visitor_team_score")
            session.add(game)
            summary["games"] += 1

            odds_payload = client.get_betting_odds(game_id=game.id, target_date=target_date)
            for odds in odds_payload:
                for leg in odds.get("legs", []):
                    bet = _upsert_bet(session, game.id, leg)
                    summary["bets"] += 1
        session.flush()
    return summary


def fetch_edges(min_edge: float = 0.05) -> Iterable[Bet]:
    """Load bets above an edge threshold."""

    with get_session() as session:
        stmt = select(Bet).where(Bet.edge >= min_edge)
        for bet in session.scalars(stmt):
            yield bet
