"""Model training utilities for multiple betting tasks."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from joblib import dump
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch import optim

from parlaylab.config import get_settings
from parlaylab.db.database import get_session
from parlaylab.db.models import ModelRun
from parlaylab.models.nn_architectures import TabularMLP
from parlaylab.models.task_registry import TASK_CONFIG, VALID_TASKS

settings = get_settings()
ARTIFACT_DIR = Path("artifacts")
ARTIFACT_DIR.mkdir(exist_ok=True)


def _prepare_dataset(task: str) -> tuple[np.ndarray, np.ndarray, StandardScaler]:
    if task not in TASK_CONFIG:
        raise ValueError(f"Unknown task '{task}'. Available: {list(TASK_CONFIG)}")
    config = TASK_CONFIG[task]
    dataset = config.builder()
    if dataset.empty:
        raise RuntimeError("No games with scores available. Ingest historical data first.")
    dataset = dataset.sort_values(by="date_home" if "date_home" in dataset.columns else "date")
    x = config.feature_fn(dataset)
    y = dataset[config.target].values
    scaler = StandardScaler()
    x_scaled = scaler.fit_transform(x)
    return x_scaled, y, scaler


def train_task(task: str, epochs: int = 20, lr: float = 1e-3) -> dict:
    x, y, scaler = _prepare_dataset(task)
    x_train, x_val, y_train, y_val = train_test_split(
        x,
        y,
        test_size=0.2,
        shuffle=False,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TabularMLP(input_dim=x.shape[1]).to(device)
    optimizer = optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.BCELoss()

    x_train_t = torch.tensor(x_train, dtype=torch.float32).to(device)
    y_train_t = torch.tensor(y_train, dtype=torch.float32).to(device)
    x_val_t = torch.tensor(x_val, dtype=torch.float32).to(device)
    model.train()
    for _ in range(epochs):
        optimizer.zero_grad()
        preds = model(x_train_t)
        loss = criterion(preds, y_train_t)
        loss.backward()
        optimizer.step()

    model.eval()
    with torch.no_grad():
        val_preds = model(x_val_t).cpu().numpy()
    metrics = {
        "log_loss": float(log_loss(y_val, val_preds, labels=[0, 1], eps=1e-15)),
        "brier": float(brier_score_loss(y_val, val_preds)),
        "accuracy": float(accuracy_score(y_val, (val_preds > 0.5).astype(int))),
    }
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    model_path = ARTIFACT_DIR / f"{task}_{timestamp}.pt"
    scaler_path = ARTIFACT_DIR / f"{task}_scaler_{timestamp}.bin"
    metrics_payload = {
        **metrics,
        "scaler_path": str(scaler_path),
        "input_dim": x.shape[1],
    }
    torch.save(model.state_dict(), model_path)
    dump(scaler, scaler_path)
    with get_session() as session:
        run = ModelRun(
            task=task,
            version=timestamp,
            metrics=metrics_payload,
            artifact_path=str(model_path),
        )
        session.add(run)

    return {"model_path": str(model_path), "scaler_path": str(scaler_path), "metrics": metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description="Train ParlayLab models")
    parser.add_argument(
        "--task",
        default="game_outcome",
        choices=list(VALID_TASKS),
        help="Task to train",
    )
    parser.add_argument("--epochs", type=int, default=20)
    args = parser.parse_args()

    result = train_task(args.task, epochs=args.epochs)
    print(f"Trained {args.task} model: {result}")


if __name__ == "__main__":
    main()
