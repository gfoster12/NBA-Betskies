# Secret Management Guide

## Local development (`.env`)
1. Copy `.env.example` → `.env`
2. Fill in real values for the required keys:
   - `BALLDONTLIE_API_KEY` (data ingestion and odds from BallDontLie)
   - `PARLAYLAB_API_KEY` (protects FastAPI endpoints; use X-API-Key header)
3. Keep `.env` out of Git (`.gitignore` already ignores `.env`/`*.env`).

## GitHub Actions (CI)
1. Go to **Settings → Secrets and variables → Actions**
2. Create repository secrets with **exact** names:
   - `BALLDONTLIE_API_KEY`
   - `PARLAYLAB_API_KEY`
3. Set each value to the raw credential (no quotes, no `KEY=` prefix).
4. The workflow installs dependencies/lints/tests without additional secrets; only integration tests hitting real APIs need these keys.

## Future hosting (e.g., Fly.io, Render, Streamlit Cloud)
1. Use the platform’s secret manager/panel to provide the same keys (TOML format for Streamlit Cloud).
2. Minimum keys:
   ```toml
   BALLDONTLIE_API_KEY = "your_real_key"
   PARLAYLAB_API_KEY = "your_api_key"
   ```
3. The FastAPI backend reads secrets via environment variables, so no code changes are required.
