"""Model inference utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import torch
from joblib import load
from sqlalchemy import select

from parlaylab.data.feature_engineering import RANKING_FEATURES, build_team_rolling_features
from parlaylab.db.database import get_session
from parlaylab.db.models import ModelRun
from parlaylab.models.nn_architectures import TabularMLP


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

    model = TabularMLP(input_dim=len(RANKING_FEATURES))
    state_dict = torch.load(artifact_path, map_location="cpu")
    model.load_state_dict(state_dict)
    model.eval()
    scaler = load(scaler_path)
    return model, scaler


def predict_team_strengths() -> Dict[int, float]:
    """Compute win probabilities for each team relative to league average."""

    features = build_team_rolling_features()
    if features.empty:
        return {}
    model, scaler = load_model()
    X = scaler.transform(features[RANKING_FEATURES].values)
    with torch.no_grad():
        probs = model(torch.tensor(X, dtype=torch.float32)).numpy()
    features = features.copy()
    features["prob"] = probs
    latest = features.sort_values("date").groupby("team_id").tail(1)
    return dict(zip(latest["team_id"], latest["prob"]))
