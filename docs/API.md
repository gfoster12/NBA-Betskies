# ParlayLab NBA API

The FastAPI backend exposes numeric/statistical data only. Custom GPT tooling should call these endpoints with the `X-API-Key` header.

## Authentication
- Set `PARLAYLAB_API_KEY` in the environment.
- Every protected endpoint requires `X-API-Key: <value>`.

## Endpoints

### `GET /health`
- Public.
- Returns `{"status": "ok"}`.

### `GET /version`
- Public.
- Returns project + model version metadata.

### `POST /generate_parlay` *(auth required)*
Request body:
```json
{
  "slate_date": "2024-12-01",
  "max_legs": 4,
  "min_edge": 0.04,
  "risk_level": "balanced",
  "bankroll": 1000
}
```
Response: `ParlayResponse` (see schemas) containing flagship parlay legs, probabilities, EV, and metadata.

### `GET /parlays` *(auth required)*
Query params: `slate_date`, `limit`.
Returns stored parlays as `ParlayResponse` objects.

### `GET /stats` *(auth required)*
Query param: `window_days` (default 30).
Returns historical summary: total parlays, win rate placeholder, ROI based on expected value, etc.

### `POST /run_daily_job` *(auth required)*
Body: `{ "target_date": "2024-12-01" }` (optional).
Triggers the existing ingestion → inference → parlay notification pipeline. Returns JSON summary.

## Example usage
```bash
curl -H "X-API-Key: $PARLAYLAB_API_KEY" http://localhost:8000/parlays?limit=5

curl -X POST -H "Content-Type: application/json" \
     -H "X-API-Key: $PARLAYLAB_API_KEY" \
     -d '{"slate_date": "2024-12-01"}' \
     http://localhost:8000/generate_parlay
```
