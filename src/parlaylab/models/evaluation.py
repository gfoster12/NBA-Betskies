"""Evaluation helpers for ParlayLab models."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return a dictionary of common classification metrics."""

    return {
        "log_loss": float(log_loss(y_true, y_pred, labels=[0, 1], eps=1e-15)),
        "brier": float(brier_score_loss(y_true, y_pred)),
        "accuracy": float(accuracy_score(y_true, (y_pred > 0.5).astype(int))),
        "roc_auc": float(roc_auc_score(y_true, y_pred)),
    }


def calibration_table(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bins: int = 10,
) -> dict[str, list[float]]:
    prob_true, prob_pred = calibration_curve(y_true, y_pred, n_bins=n_bins, strategy="uniform")
    return {"prob_true": prob_true.tolist(), "prob_pred": prob_pred.tolist()}


def plot_calibration(y_true: np.ndarray, y_pred: np.ndarray, n_bins: int = 10) -> plt.Figure:
    """Return a matplotlib figure for calibration plots."""

    data = calibration_table(y_true, y_pred, n_bins)
    fig, ax = plt.subplots(figsize=(4, 4))
    ax.plot([0, 1], [0, 1], "--", color="gray", label="Perfect")
    ax.plot(data["prob_pred"], data["prob_true"], marker="o", label="Model")
    ax.set_xlabel("Predicted probability")
    ax.set_ylabel("Actual frequency")
    ax.legend()
    ax.set_title("Calibration")
    fig.tight_layout()
    return fig
