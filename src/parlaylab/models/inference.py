"""Model inference utilities."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import torch
from joblib import load
from sqlalchemy import select

from parlaylab.data.feature_engineering import (
    RANKING_FEATURES,
)
from parlaylab.db.database import get_session
from parlaylab.db.models import ModelRun
from parlaylab.models.nn_architectures import TabularMLP
from parlaylab.models.task_registry import TASK_CONFIG


def _latest_run(task: str) -> ModelRun | None:
    with get_session() as session:
        stmt = select(ModelRun).where(ModelRun.task == task).order_by(ModelRun.trained_at.desc())
        return session.execute(stmt).scalars().first()


def load_model(task: str = "game_outcome") -> tuple[TabularMLP, object]:
    """Load the latest trained model and scaler."""

    run = _latest_run(task)
    if not run:
        raise RuntimeError("No trained model found. Run training first.")
    artifact_path = Path(run.artifact_path)
    scaler_path = Path(run.metrics.get("scaler_path"))
    if not artifact_path.exists() or not scaler_path.exists():
        raise FileNotFoundError("Model artifacts missing. Retrain the model.")

    input_dim = int(run.metrics.get("input_dim", len(RANKING_FEATURES)))
    model = TabularMLP(input_dim=input_dim)
    state_dict = torch.load(artifact_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    scaler = load(scaler_path)
    return model, scaler


def _run_task(task: str) -> tuple[pd.DataFrame, np.ndarray]:
    config = TASK_CONFIG.get(task)
    if not config:
        raise ValueError(f"Unknown task '{task}'")
    dataset = config.builder()
    if dataset.empty:
        return dataset, np.array([])
    model, scaler = load_model(task)
    X = config.feature_fn(dataset)
    X_scaled = scaler.transform(X)
    with torch.no_grad():
        probs = model(torch.tensor(X_scaled, dtype=torch.float32)).numpy()
    return dataset, probs


def predict_matchup_probabilities(task: str = "game_outcome") -> dict[int, dict[str, float]]:
    """Return probabilities for matchup-style tasks keyed by game ID."""

    dataset, probs = _run_task(task)
    if dataset.empty:
        return {}
    dataset = dataset.copy()
    dataset["model_prob"] = probs
    predictions: dict[int, dict[str, float]] = {}
    for _, row in dataset.iterrows():
        predictions[int(row["game_id"])] = {
            "home_team_id": int(row["team_id_home"]),
            "away_team_id": int(row["team_id_away"]),
            "home_prob": float(row["model_prob"]),
            "away_prob": float(1 - row["model_prob"]),
        }
    return predictions


def predict_player_points_probabilities() -> dict[int, float]:
    """Return star-prop proxy probabilities keyed by team ID."""

    dataset, probs = _run_task("player_points")
    if dataset.empty:
        return {}
    dataset = dataset.copy()
    dataset["model_prob"] = probs
    return dict(zip(dataset["team_id"], dataset["model_prob"]))


def predict_team_strengths() -> dict[int, float]:
    """Backward-compatible alias for per-team win probabilities."""

    matchup_preds = predict_matchup_probabilities("game_outcome")
    results: dict[int, float] = {}
    for data in matchup_preds.values():
        results[data["home_team_id"]] = data["home_prob"]
        results[data["away_team_id"]] = data["away_prob"]
    return results
