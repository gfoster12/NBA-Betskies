"""Shared task registry for ParlayLab models."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd

from parlaylab.data.feature_engineering import (
    RANKING_FEATURES,
    build_matchup_dataset,
    build_player_prop_dataset,
)

MATCHUP_BASE_FEATURES = RANKING_FEATURES + ["is_home_rate"]
PLAYER_FEATURES = RANKING_FEATURES + ["is_home_rate"]


def matchup_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    columns = []
    for feature in MATCHUP_BASE_FEATURES:
        columns.append(df[f"{feature}_home"].values - df[f"{feature}_away"].values)
    columns.append(df["pace_home"].values + df["pace_away"].values)
    return np.column_stack(columns)


def player_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    return df[PLAYER_FEATURES].values


@dataclass
class TaskConfig:
    target: str
    builder: Callable[[], pd.DataFrame]
    feature_fn: Callable[[pd.DataFrame], np.ndarray]


TASK_CONFIG: dict[str, TaskConfig] = {
    "game_outcome": TaskConfig(
        target="home_win",
        builder=build_matchup_dataset,
        feature_fn=matchup_feature_matrix,
    ),
    "spread_cover": TaskConfig(
        target="spread_cover",
        builder=build_matchup_dataset,
        feature_fn=matchup_feature_matrix,
    ),
    "total_points": TaskConfig(
        target="total_over_220",
        builder=build_matchup_dataset,
        feature_fn=matchup_feature_matrix,
    ),
    "player_points": TaskConfig(
        target="player_points_over",
        builder=build_player_prop_dataset,
        feature_fn=player_feature_matrix,
    ),
}

VALID_TASKS: tuple[str, ...] = tuple(TASK_CONFIG.keys())
