"""Sanity test ensuring the FastAPI app imports."""

from parlaylab.api.server import app


def test_app_import() -> None:
    assert app is not None
