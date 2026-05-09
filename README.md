# OC2 Local Job Search (MVP Architecture)

Lightweight, local-first job-search web app scaffold designed for a single user, 40-50 target companies, and Qwen 3B via Ollama across extraction/matching workflows.

## Stack
- FastAPI backend
- SQLite (SQLAlchemy)
- APScheduler for periodic search cycles
- Ollama (`qwen2.5:3b` configurable)
- httpx + BeautifulSoup parsing
- Optional Playwright fallback for JS-heavy pages

## Quickstart
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API highlights
- `POST /profile`
- `POST /profile/upload-cv`
- `GET /companies`
- `POST /companies/discover-career-sites` (internet-assisted discovery)
- `POST /search/run` (Firecrawl-backed job discovery)
- `GET /jobs/matches`
- `POST /jobs/report/email`

## Firecrawl and email setup
Copy `.env.example` to `.env` and set either `FIRECRAWL_API_KEY` for the current local session or use:

```bash
python scripts/encrypt_secret.py
```

Then paste the generated `FIRECRAWL_SECRET_KEY` and `FIRECRAWL_API_KEY_ENCRYPTED` values into `.env`.

Email reports use `JOB_REPORT_TO_EMAIL` as both sender and recipient unless `SMTP_FROM_EMAIL` is set. For Gmail, set `SMTP_USERNAME=2001siddi@gmail.com` and use a Gmail app password as `SMTP_PASSWORD`; normal account passwords are not accepted by Gmail SMTP.

## Notes
- Company/search behavior is configuration-driven via JSON, not hardcoded per company logic.
- Deterministic + LLM hybrid ranking is used.
- LinkedIn/Indeed scraping is intentionally avoided in code paths; official/company pages are preferred.
