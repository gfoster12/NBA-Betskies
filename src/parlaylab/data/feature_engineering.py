"""Feature engineering utilities."""

from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd
from sqlalchemy import select

from parlaylab.db.database import get_session
from parlaylab.db.models import Game


RANKING_FEATURES = ["off_rating", "def_rating", "pace", "rebound_pct", "turnover_pct"]


def _games_dataframe() -> pd.DataFrame:
    with get_session() as session:
        games = list(session.scalars(select(Game)))
    rows: List[dict] = []
    for game in games:
        if game.home_score is None or game.away_score is None:
            continue
        rows.append(
            {
                "game_id": game.id,
                "date": game.date,
                "team_id": game.home_team_id,
                "opponent_id": game.away_team_id,
                "points_for": game.home_score,
                "points_against": game.away_score,
                "is_home": 1,
            }
        )
        rows.append(
            {
                "game_id": game.id,
                "date": game.date,
                "team_id": game.away_team_id,
                "opponent_id": game.home_team_id,
                "points_for": game.away_score,
                "points_against": game.home_score,
                "is_home": 0,
            }
        )
    return pd.DataFrame(rows)


def build_team_rolling_features(window: int = 5) -> pd.DataFrame:
    """Compute rolling team metrics for upcoming modeling."""

    df = _games_dataframe()
    if df.empty:
        return df
    df = df.sort_values("date")
    grouped = []
    for team_id, team_df in df.groupby("team_id"):
        roll = team_df.set_index("date").rolling(window=window, min_periods=1)
        stats = pd.DataFrame(
            {
                "team_id": team_df["team_id"],
                "date": team_df["date"],
                "off_rating": roll["points_for"].mean() * 100 / roll.count()["points_for"],
                "def_rating": roll["points_against"].mean() * 100 / roll.count()["points_against"],
                "pace": roll["points_for"].mean() + roll["points_against"].mean(),
                "rebound_pct": roll["points_for"].sum() / (roll["points_for"].sum() + roll["points_against"].sum()),
                "turnover_pct": 1 - roll["points_for"].mean() / (roll["points_for"].mean() + 1e-6),
                "is_home_rate": roll["is_home"].mean(),
            }
        ).reset_index(drop=True)
        grouped.append(stats)
    feature_df = pd.concat(grouped, ignore_index=True)
    feature_df = feature_df.replace([np.inf, -np.inf], pd.NA)
    feature_df = feature_df.ffill().bfill().fillna(0.0)
    return feature_df


def summarize_features(feature_df: pd.DataFrame) -> Dict[str, float]:
    """Provide quick descriptive stats for monitoring."""

    summary: Dict[str, float] = {}
    if feature_df.empty:
        return summary
    for column in feature_df.columns:
        if column in {"team_id", "date"}:
            continue
        summary[f"{column}_mean"] = float(feature_df[column].mean())
        summary[f"{column}_std"] = float(feature_df[column].std())
    return summary
