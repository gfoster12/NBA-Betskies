# Deploying the ParlayLab API

The backend is a standard FastAPI application and can run anywhere that supports Python 3.11+, such as Render, Railway, Fly.io, or Azure Container Apps.

## Required environment variables
- `PARLAYLAB_API_KEY` – used to authenticate API calls (X-API-Key header)
- `BALLDONTLIE_API_KEY` – access token for the BallDontLie GOAT API
- Optional: `DATABASE_URL`, tuning knobs (`EDGE_THRESHOLD`, etc.)

## Running locally
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .[dev]
export PARLAYLAB_API_KEY=local-secret
export BALLDONTLIE_API_KEY=sk_test...
python -m parlaylab.api.main  # starts uvicorn on port 8000
```

## Deploying to a managed host (example: Render)
1. Create a new Web Service pointing to this repo and the `python -m parlaylab.api.main` start command.
2. Set environment variables in the provider dashboard (same as above).
3. Expose port 8000 (or set `PORT` env and the entrypoint will respect it).
4. Optionally schedule the daily job via cron hitting the `/run_daily_job` endpoint or running `python -m parlaylab.scheduling.jobs`

## Exporting OpenAPI for GPT Actions
Use the helper script:
```bash
python scripts/export_openapi.py
```
The schema is written to `api_spec/openapi.json`. If you have a public base URL, set `PUBLIC_API_BASE_URL=https://api.yourdomain.com` before running the script so the generated schema advertises the correct server.

## CI/CD
The GitHub Actions workflow installs dependencies, runs `ruff`, and executes the unit tests. Ensure `PARLAYLAB_API_KEY` and `BALLDONTLIE_API_KEY` secrets are configured under Settings → Secrets → Actions.
