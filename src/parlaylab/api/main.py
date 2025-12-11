"""CLI entrypoint to run the ParlayLab FastAPI server."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("parlaylab.api.server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
