# Secret Management Guide

## Local development (`.env`)
1. Copy `.env.example` → `.env`
2. Fill in real values for the required keys:
   - `BALLDONTLIE_API_KEY` (data ingestion and odds from BallDontLie)
   - `OPENAI_API_KEY` (LLM explanations + marketing agent)
3. Optional notifier settings (SMTP + Twilio) are used by the notification service and daily scheduler.
4. Keep `.env` out of Git (`.gitignore` already ignores `.env`/`*.env`).

## GitHub Actions (CI)
1. Go to **Settings → Secrets and variables → Actions**
2. Create repository secrets with **exact** names:
   - `BALLDONTLIE_API_KEY`
   - `OPENAI_API_KEY`
   - `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_USER`, `EMAIL_PASSWORD`, `EMAIL_FROM`
   - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
3. Set each value to the raw credential (no quotes, no `KEY=` prefix).
4. `.github/workflows/tests.yml` maps these secrets into environment variables via an `env:` block, so `ruff`, tests, and compile steps can read them just like local `.env` values.

## Future Streamlit Cloud deployment
1. In Streamlit Cloud, open your app’s **Secrets** panel.
2. Paste the same keys using TOML syntax, e.g.:
   ```toml
   BALLDONTLIE_API_KEY = "your_real_key"
   OPENAI_API_KEY = "your_real_key"
   EMAIL_HOST = "smtp.example.com"
   EMAIL_PORT = "587"
   EMAIL_USER = "your_user"
   EMAIL_PASSWORD = "your_pass"
   EMAIL_FROM = "parlaylab@example.com"
   TWILIO_ACCOUNT_SID = "ACxxx"
   TWILIO_AUTH_TOKEN = "abc123"
   TWILIO_FROM_NUMBER = "+15551234567"
   ```
3. The app code always reads secrets via `os.getenv()` / `get_settings()`, so no code changes are required for Streamlit.
