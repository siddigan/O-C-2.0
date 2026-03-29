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
- `POST /search/run`
- `GET /jobs/matches`

## Notes
- Company/search behavior is configuration-driven via JSON, not hardcoded per company logic.
- Deterministic + LLM hybrid ranking is used.
- LinkedIn/Indeed scraping is intentionally avoided in code paths; official/company pages are preferred.
