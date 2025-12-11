"""Feature engineering utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy import select

from parlaylab.db.database import get_session
from parlaylab.db.models import Game

RANKING_FEATURES = ["off_rating", "def_rating", "pace", "rebound_pct", "turnover_pct"]
PLAYER_PROP_THRESHOLD = 25.0


def _games_dataframe() -> pd.DataFrame:
    with get_session() as session:
        games = list(session.scalars(select(Game)))
    rows: list[dict] = []
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
    for _, team_df in df.groupby("team_id"):
        roll = team_df.set_index("date").rolling(window=window, min_periods=1)
        stats = pd.DataFrame(
            {
                "game_id": team_df["game_id"],
                "team_id": team_df["team_id"],
                "date": team_df["date"],
                "is_home": team_df["is_home"],
                "points_for": team_df["points_for"],
                "points_against": team_df["points_against"],
                "off_rating": roll["points_for"].mean()
                * 100
                / roll.count()["points_for"],
                "def_rating": roll["points_against"].mean()
                * 100
                / roll.count()["points_against"],
                "pace": roll["points_for"].mean() + roll["points_against"].mean(),
                "rebound_pct": roll["points_for"].sum()
                / (roll["points_for"].sum() + roll["points_against"].sum()),
                "turnover_pct": 1
                - roll["points_for"].mean() / (roll["points_for"].mean() + 1e-6),
                "is_home_rate": roll["is_home"].mean(),
            }
        ).reset_index(drop=True)
        grouped.append(stats)
    feature_df = pd.concat(grouped, ignore_index=True)
    feature_df = feature_df.replace([np.inf, -np.inf], pd.NA)
    feature_df = feature_df.ffill().bfill().fillna(0.0)
    return feature_df


def summarize_features(feature_df: pd.DataFrame) -> dict[str, float]:
    """Provide quick descriptive stats for monitoring."""

    summary: dict[str, float] = {}
    if feature_df.empty:
        return summary
    for column in feature_df.columns:
        if column in {"team_id", "date"}:
            continue
        summary[f"{column}_mean"] = float(feature_df[column].mean())
        summary[f"{column}_std"] = float(feature_df[column].std())
    return summary


def build_matchup_dataset(window: int = 5) -> pd.DataFrame:
    """Return merged home/away features with labels for multiple tasks."""

    features = build_team_rolling_features(window)
    if features.empty:
        return features
    home = features[features["is_home"] == 1]
    away = features[features["is_home"] == 0]
    matchup = home.merge(
        away,
        on="game_id",
        suffixes=("_home", "_away"),
    )
    if matchup.empty:
        return matchup
    matchup["home_win"] = (matchup["points_for_home"] > matchup["points_for_away"]).astype(int)
    matchup["spread_cover"] = (
        (matchup["points_for_home"] - matchup["points_against_home"]) > 0
    ).astype(int)
    matchup["total_over_220"] = (
        (matchup["points_for_home"] + matchup["points_for_away"]) > 220
    ).astype(int)
    matchup["game_total"] = matchup["points_for_home"] + matchup["points_for_away"]
    return matchup


def build_player_prop_dataset(
    window: int = 5,
    threshold: float = PLAYER_PROP_THRESHOLD,
) -> pd.DataFrame:
    """Approximate player prop labels from team-level production."""

    features = build_team_rolling_features(window)
    if features.empty:
        return features
    df = features.copy()
    df["star_points_est"] = df["points_for"] * 0.3
    df["player_points_over"] = (df["star_points_est"] >= threshold).astype(int)
    return df
