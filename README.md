# ParlayLab NBA

ParlayLab NBA is a full-stack sports analytics platform that ingests BALLDONTLIE GOAT data, trains probabilistic models, constructs +EV parlays, and distributes daily picks via Streamlit dashboards, notifications, and marketing content powered by GPT-5.1.

> **Responsible gaming:** This is an analytics tool for educational/entertainment use. Wager only what you can afford to lose and follow local laws (18+).

## Features
- Automated ingestion of teams/games/odds with rolling feature engineering stored in SQLite (swap-ready for Postgres).
- Hybrid ML stack (PyTorch tabular MLP + scikit-learn utilities) with daily retraining hooks, metrics logging, and artifact persistence across moneyline/spread/total/player-prop tasks.
- Parlay engine with correlation filters, EV + fractional Kelly bankroll sizing, and flagship/alternative outputs.
- FastAPI backend exposing health, parlay generation, and stats endpoints (ready for GPT Actions).
- Notification layer with SMTP email + Twilio SMS (rate limited) plus documented cron-style scheduler.
- Tests, docs, GitHub Actions CI, and typed config.

## Quickstart
1. **Python env**
   ```bash
   python3.11 -m venv .venv && source .venv/bin/activate
   pip install -U pip
   pip install -e .[dev]
   ```
2. **Environment variables** – copy `.env.example` to `.env` and fill in:
   - `BALLDONTLIE_API_KEY` *(GOAT subscription; never commit this value)*
   - SMTP settings (`EMAIL_*`), `ADMIN_PASSWORD`, `DATABASE_URL`, etc.
3. **Initialize DB**
   ```bash
   python -c "from parlaylab.db.models import Base; from parlaylab.db.database import engine; Base.metadata.create_all(engine)"
   ```
4. **Ingest data**
   ```bash
   python -c "from datetime import date; from parlaylab.data.ingestion import sync_historical_data, sync_daily; sync_historical_data(2022, 2023); sync_daily(date.today())"
   ```
5. **Train models** – choose from `game_outcome`, `spread_cover`, `total_points`, `player_points`
   ```bash
   python -m parlaylab.models.training --task game_outcome --epochs 30
   python -m parlaylab.models.training --task spread_cover --epochs 30
   python -m parlaylab.models.training --task total_points --epochs 30
   python -m parlaylab.models.training --task player_points --epochs 30
   ```
6. **Run the API server**
   ```bash
   python -m parlaylab.api.main
   # equivalent: uvicorn parlaylab.api.server:app --host 0.0.0.0 --port 8000
   ```
7. **Daily job (scheduler/cron)**
   ```bash
   python -m parlaylab.scheduling.jobs
   ```
   (Documented in `DEPLOYMENT.md` for cron usage.)

### Syncing `requirements.txt`
Dependencies live in `pyproject.toml`. Whenever you change them, regenerate `requirements.txt` (used by some deploy targets) via:
```bash
python scripts/sync_requirements.py --with-extras
```

## Tests & Quality
```bash
pytest
ruff check .
```

GitHub Actions workflow (`.github/workflows/tests.yml`) installs dependencies and runs the same pytest suite.

## Docs
- `docs/ARCHITECTURE.md` – module/data-flow overview.
- `docs/ML_PIPELINE.md` – feature sets, training loop, and evaluation methodology.
- `docs/DEPLOYMENT.md` – Streamlit Cloud setup, scheduling strategy, and env requirements.

## Configuration summary
Settings live in `parlaylab/config.py` (Pydantic). Key knobs:
- `EDGE_THRESHOLD`, `KELLY_FRACTION`, `DEFAULT_BANKROLL`, `SCHEDULER_RUN_HOUR`.
- `MAX_CORRELATION_SCORE`, `CORRELATION_PENALTY_WEIGHT` for overlap penalties.
- Notification mode + SMTP credentials.
- Twilio SMS keys (`TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`) + `SMS_RATE_LIMIT_PER_MINUTE`.
- Database URL (SQLite default, Postgres-ready).

Refer to the docs for extensibility ideas such as richer correlation modeling, additional prop markets, or production notification providers (Twilio, SES, etc.).
