"""Export the FastAPI OpenAPI schema for GPT Actions."""

from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi.encoders import jsonable_encoder

from parlaylab.api.server import app

OUTPUT_PATH = Path("api_spec/openapi.json")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


def main() -> None:
    schema = app.openapi()
    public_base = os.getenv("PUBLIC_API_BASE_URL")
    if public_base:
        schema["servers"] = [{"url": public_base.rstrip("/")}]
    OUTPUT_PATH.write_text(json.dumps(jsonable_encoder(schema), indent=2))
    print(f"OpenAPI schema written to {OUTPUT_PATH}")


if __name__ == "__main__":  # pragma: no cover
    main()
