"""Model training utilities."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Tuple

import numpy as np
import torch
from joblib import dump
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch import optim

from parlaylab.config import get_settings
from parlaylab.data.feature_engineering import RANKING_FEATURES, build_team_rolling_features
from parlaylab.db.database import get_session
from parlaylab.db.models import ModelRun
from parlaylab.models.nn_architectures import TabularMLP

settings = get_settings()
ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)


def _prepare_dataset() -> Tuple[np.ndarray, np.ndarray, StandardScaler]:
    features = build_team_rolling_features()
    if features.empty:
        raise RuntimeError("No games with scores available. Ingest historical data first.")
    features = features.sort_values("date")
    features["target"] = (features["off_rating"] > features["def_rating"]).astype(int)
    X = features[RANKING_FEATURES].values
    y = features["target"].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, y, scaler


def train_game_outcome_model(epochs: int = 20, lr: float = 1e-3) -> dict:
    """Train a simple neural net to predict win probability."""

    X, y, scaler = _prepare_dataset()
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TabularMLP(input_dim=X.shape[1]).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.BCELoss()

    X_train_t = torch.tensor(X_train, dtype=torch.float32).to(device)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).to(device)
    X_val_t = torch.tensor(X_val, dtype=torch.float32).to(device)
    y_val_t = torch.tensor(y_val, dtype=torch.float32).to(device)

    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        preds = model(X_train_t)
        loss = criterion(preds, y_train_t)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        val_preds = model(X_val_t).cpu().numpy()
    metrics = {
        "log_loss": float(log_loss(y_val, val_preds, labels=[0, 1], eps=1e-15)),
        "brier": float(brier_score_loss(y_val, val_preds)),
        "accuracy": float(accuracy_score(y_val, (val_preds > 0.5).astype(int))),
    }

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_path = ARTIFACT_DIR / f"game_outcome_{timestamp}.pt"
    scaler_path = ARTIFACT_DIR / f"game_outcome_scaler_{timestamp}.bin"
    torch.save(model.state_dict(), model_path)
    dump(scaler, scaler_path)

    with get_session() as session:
        run = ModelRun(
            task="game_outcome",
            version=timestamp,
            metrics={**metrics, "scaler_path": str(scaler_path)},
            artifact_path=str(model_path),
        )
        session.add(run)

    return {"model_path": str(model_path), "scaler_path": str(scaler_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ParlayLab models")
    parser.add_argument("--task", default="game_outcome", choices=["game_outcome"], help="Task to train")
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()

    if args.task == "game_outcome":
        result = train_game_outcome_model(epochs=args.epochs)
        print(f"Trained game outcome model: {result}")


if __name__ == "__main__":
    main()
