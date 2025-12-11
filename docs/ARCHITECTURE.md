# Architecture Overview

ParlayLab NBA is split into cohesive layers that can be independently iterated:

1. **Data access layer (`parlaylab.data`, `parlaylab.db`)**
   - `balldontlie_client.py` authenticates with the GOAT API via `BALLDONTLIE_API_KEY`.
   - `ingestion.py` orchestrates historical + daily syncs and persists normalized rows via SQLAlchemy models defined in `db/models.py`.
   - `feature_engineering.py` reads from the DB and produces rolling team/player metrics that serve as inputs to the ML stack.

2. **Modeling layer (`parlaylab.models`)**
   - `nn_architectures.py` hosts PyTorch modules (currently a tabular MLP) that power probability estimation.
   - `training.py` trains tasks (game outcome baseline), logs metrics in `ModelRun`, and stores artifacts under `artifacts/` with timestamps.
   - `inference.py` reloads the latest artifacts to generate per-team strength estimates; `evaluation.py` centralizes metric/calibration utilities.

3. **Parlay intelligence (`parlaylab.parlays`)**
   - `types.py` defines dataclasses for legs + recommendations.
   - `engine.py` converts +EV bets into correlation-safe parlays, evaluates payout/EV, and applies fractional Kelly staking.

4. **Delivery + automation**
   - `notifications/` implements SMTP + SMS stubs behind a `NotificationService`.
   - `agents/` wraps OpenAI: `llm_client.py` handles Chat Completions, `marketing_agent.py` crafts Instagram-ready content.
   - `scheduling/jobs.py` ties ingestion → inference → parlay selection → notifications/marketing for cron-style execution.

5. **Presentation (`app/streamlit_app.py`)**
   - Streamlit UI surfaces flagship parlays, model insights, an interactive builder, marketing assistant controls, and subscriber CRUD guarded by `ADMIN_PASSWORD`.

Data flow:
```
BALLDONTLIE API → ingestion → SQLite (via SQLAlchemy models)
                    ↓
             feature_engineering
                    ↓
               ML training → artifacts + ModelRun metadata
                    ↓
              inference + bet scoring
                    ↓
             parlay engine (EV + Kelly)
                    ↓
        Streamlit UI / Notifications / Marketing Agent
```

Each component is designed behind clean abstractions, enabling future swaps (e.g., Postgres, more advanced neural nets, third-party SMS gateways) without disrupting other layers.
