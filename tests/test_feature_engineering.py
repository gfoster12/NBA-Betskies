"""Feature engineering tests."""

from __future__ import annotations

import pandas as pd

from parlaylab.data import feature_engineering as fe


def test_build_team_rolling_features(monkeypatch) -> None:
    sample = pd.DataFrame(
        [
            {"game_id": 1, "date": pd.Timestamp("2024-01-01"), "team_id": 1, "opponent_id": 2, "points_for": 110, "points_against": 100, "is_home": 1},
            {"game_id": 1, "date": pd.Timestamp("2024-01-01"), "team_id": 2, "opponent_id": 1, "points_for": 100, "points_against": 110, "is_home": 0},
            {"game_id": 2, "date": pd.Timestamp("2024-01-05"), "team_id": 1, "opponent_id": 3, "points_for": 120, "points_against": 90, "is_home": 0},
        ]
    )
    monkeypatch.setattr(fe, "_games_dataframe", lambda: sample)
    features = fe.build_team_rolling_features(window=2)
    assert not features.empty
    for column in fe.RANKING_FEATURES:
        assert column in features.columns
    assert "game_id" in features.columns


def test_summarize_features(monkeypatch) -> None:
    df = pd.DataFrame({"team_id": [1, 1], "date": pd.date_range("2024-01-01", periods=2), "off_rating": [110, 115], "def_rating": [100, 105], "pace": [200, 210], "rebound_pct": [0.52, 0.54], "turnover_pct": [0.12, 0.1]})
    summary = fe.summarize_features(df)
    assert "off_rating_mean" in summary
    assert summary["def_rating_mean"] > 0


def test_build_matchup_and_player_datasets(monkeypatch) -> None:
    sample = pd.DataFrame(
        [
            {"game_id": 1, "date": pd.Timestamp("2024-01-01"), "team_id": 1, "opponent_id": 2, "points_for": 110, "points_against": 100, "is_home": 1},
            {"game_id": 1, "date": pd.Timestamp("2024-01-01"), "team_id": 2, "opponent_id": 1, "points_for": 100, "points_against": 110, "is_home": 0},
            {"game_id": 2, "date": pd.Timestamp("2024-01-05"), "team_id": 3, "opponent_id": 4, "points_for": 118, "points_against": 99, "is_home": 1},
            {"game_id": 2, "date": pd.Timestamp("2024-01-05"), "team_id": 4, "opponent_id": 3, "points_for": 99, "points_against": 118, "is_home": 0},
        ]
    )
    monkeypatch.setattr(fe, "_games_dataframe", lambda: sample)
    matchup = fe.build_matchup_dataset(window=2)
    assert not matchup.empty
    assert {"home_win", "spread_cover", "total_over_220"} <= set(matchup.columns)
    player_df = fe.build_player_prop_dataset(window=2)
    assert not player_df.empty
    assert "player_points_over" in player_df.columns
