"""ParlayLab NBA core package."""

from importlib import metadata

__all__ = ["__version__"]

try:
    __version__ = metadata.version("parlaylab-nba")
except metadata.PackageNotFoundError:  # pragma: no cover - local dev fallback
    __version__ = "0.0.0"
