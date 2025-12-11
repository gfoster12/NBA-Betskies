"""CLI entrypoint to run the ParlayLab FastAPI server."""

from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("parlaylab.api.server:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":  # pragma: no cover
    main()
