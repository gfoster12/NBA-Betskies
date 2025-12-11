"""Neural network architectures for ParlayLab models."""

from __future__ import annotations

from typing import Iterable, List

import torch
from torch import nn


class TabularMLP(nn.Module):
    """Simple fully connected network for tabular data."""

    def __init__(self, input_dim: int, hidden_dims: Iterable[int] | None = None, dropout: float = 0.2):
        super().__init__()
        hidden_dims = list(hidden_dims or [256, 128, 64])
        layers: List[nn.Module] = []
        in_dim = input_dim
        for hidden in hidden_dims:
            layers.extend([nn.Linear(in_dim, hidden), nn.BatchNorm1d(hidden), nn.ReLU(), nn.Dropout(dropout)])
            in_dim = hidden
        layers.append(nn.Linear(in_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # type: ignore[override]
        return torch.sigmoid(self.net(x)).squeeze(-1)
