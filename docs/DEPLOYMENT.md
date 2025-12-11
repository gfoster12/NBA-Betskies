# Deployment Guide

## Streamlit Cloud (or similar PaaS)
1. Push this repository to GitHub.
2. In Streamlit Cloud, create a new app pointing to `app/streamlit_app.py` on the desired branch.
3. Configure secrets / environment variables via Streamlit Cloud's Secrets manager:
   - `BALLDONTLIE_API_KEY`
   - `OPENAI_API_KEY`, `OPENAI_MODEL`
   - `DATABASE_URL` (for prod prefer a managed Postgres instance rather than SQLite).
   - SMTP credentials (`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM`).
   - `ADMIN_PASSWORD`, `EDGE_THRESHOLD`, `KELLY_FRACTION`, etc.
4. Pre-run migrations/DB bootstrap on the target database before bringing the app online.
5. Attach optional monitoring (Streamlit metrics, OpenTelemetry exporter, or a log-forwarding agent) if running in production.

## Scheduling daily jobs
- `parlaylab/scheduling/jobs.py` exposes `run_daily_job()` that performs ingestion → inference → flagship parlay selection → notifications/marketing.
- Recommended cron entry (Linux) once the virtualenv is activated:
  ```cron
  0 9 * * * cd /path/to/repo && /path/to/venv/bin/python -m parlaylab.scheduling.jobs >> logs/parlaylab.log 2>&1
  ```
- Ensure the cron environment exports the same `.env` variables (e.g., `set -a; source /path/to/.env; set +a`).
- For Streamlit Cloud, schedule jobs externally (GitHub Actions, AWS Lambda, or a lightweight VM) that invokes the module via REST/SNS or a CLI runner.

## Notifications & credentials
- Email backend uses generic SMTP with STARTTLS; for production configure a reliable provider (SES, SendGrid) and rotate passwords regularly.
- `sms_backend.py` is a logging stub. Swap with Twilio/Vonage by following the same interface (implement `send(body, recipients)`).

## Scalability considerations
- Replace SQLite with Postgres by setting `DATABASE_URL` accordingly (SQLAlchemy models are portable).
- Move artifact storage to S3/GCS when multiple app instances need shared models.
- Wrap ingestion/training in a workflow orchestrator for retries, alerting, and lineage.
- Harden secrets using a vault service rather than `.env` in multi-user deployments.
