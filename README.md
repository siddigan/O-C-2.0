# OC2 Local Job Search

OC2 is a local-first job search dashboard for tracking a curated list of target companies, discovering relevant roles, ranking them against a user profile, and optionally sending email reports.

The app is designed for one local user and a focused company list. It uses FastAPI for the backend, SQLite for storage, a static browser UI, Firecrawl for job discovery, and Ollama for CV parsing and match explanations.

## Features

- Create and update a job-search profile.
- Upload a CV and store the parsed profile summary.
- Maintain a prioritized target-company list with career-site URLs.
- Discover missing career-site URLs.
- Run company job searches manually or on a schedule.
- Store deduplicated jobs in SQLite.
- Rank jobs against target roles, skills, location preferences, seniority, and company priority.
- Send a top-jobs email report.
- View backend and UI logs from the browser.

## Tech Stack

- Python 3.12
- FastAPI
- Uvicorn
- SQLite and SQLAlchemy
- APScheduler
- Pydantic settings
- Firecrawl API
- Ollama, default model `qwen2.5:3b`
- Static HTML, CSS, and JavaScript frontend

## Project Layout

```text
app/
  api/routes.py             API route definitions
  core/settings.py          Environment-backed configuration
  core/logging_config.py    File and console logging
  db/session.py             SQLAlchemy engine/session setup
  models/models.py          Profile, Company, Job, JobMatch tables
  services/                 Profile, company, search, match, email services
frontend/
  index.html                Browser UI
  app.js                    UI behavior and API calls
  style.css                 UI styling
scripts/
  add_companies_seed.py     Seed companies with known career URLs
  seed_companies.py         Seed company names from JSON config
  discover_career_sites.py  Career-site discovery helper
  encrypt_secret.py         Encrypt Firecrawl API key for .env
data/cv/                    Uploaded CV files
logs/                       App and server logs
oc2.db                      Local SQLite database
run.ps1                     Windows server launcher
```

## Quick Start

From PowerShell in the project root:

```powershell
.\run.ps1 -Host 127.0.0.1 -Port 8000 -Reload
```

Then open:

```text
http://127.0.0.1:8000/
```

The root path redirects to the dashboard at `/ui/`.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","scheduler_enabled":true}
```

## Setup From Scratch

This repository includes a local `.py312` Python runtime and `run.ps1` uses it automatically. If you want to use your own virtual environment instead:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

On macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Configuration

Copy `.env.example` to `.env` and edit the values you need:

```powershell
Copy-Item .env.example .env
```

Important settings:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLite database path. Defaults to `sqlite:///./oc2.db`. |
| `OLLAMA_URL` | Local Ollama server URL. Defaults to `http://localhost:11434`. |
| `OLLAMA_MODEL` | Ollama model used for JSON parsing/explanations. Defaults to `qwen2.5:3b`. |
| `SCHEDULER_ENABLED` | Enables the 12-hour background search cycle. |
| `FIRECRAWL_API_KEY` | Plain Firecrawl API key for local job discovery. |
| `FIRECRAWL_API_KEY_ENCRYPTED` | Encrypted Firecrawl API key alternative. |
| `FIRECRAWL_SECRET_KEY` | Fernet key used to decrypt the encrypted Firecrawl key. |
| `SEARCH_BATCH_SIZE` | Number of enabled companies processed per search run. |
| `SEARCH_ALLOW_SAMPLE_FALLBACK` | Allows sample placeholder jobs when search returns none. Keep `false` for real runs. |
| `JOB_REPORT_AFTER_SEARCH` | Sends email report after `/search/run` when SMTP is configured. |
| `JOB_REPORT_ON_SHUTDOWN` | Sends email report when the app shuts down. |
| `SMTP_*` | SMTP configuration for job reports. |

## Ollama

Install and start Ollama separately, then pull the configured model:

```powershell
ollama pull qwen2.5:3b
ollama serve
```

If Ollama is unavailable, the app falls back to simple default explanations for match scoring, but CV parsing and richer match reasons will be limited.

## Firecrawl

Firecrawl is used by the search service to discover jobs from company career sites. You can place a plain key in `.env`:

```text
FIRECRAWL_API_KEY="your-key"
```

Or generate encrypted values:

```powershell
.\.py312\python.exe scripts\encrypt_secret.py
```

Paste the printed `FIRECRAWL_SECRET_KEY` and `FIRECRAWL_API_KEY_ENCRYPTED` values into `.env`.

## Email Reports

Email reports use SMTP. For Gmail, use an app password, not your normal account password.

Minimum Gmail-style configuration:

```text
JOB_REPORT_TO_EMAIL="you@example.com"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="you@example.com"
SMTP_PASSWORD="your-gmail-app-password"
SMTP_FROM_EMAIL="you@example.com"
SMTP_STARTTLS=true
```

You can send a sample report from the API:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/jobs/report/email?sample=true"
```

## Database

The default database is `oc2.db` in the project root. Tables are created automatically at application startup.

Main tables:

- `profiles`: one local user profile and CV summary.
- `companies`: target companies, priority, enabled flag, and career URL.
- `jobs`: discovered jobs with dedupe hash and apply URL.
- `job_matches`: generated ranking results for a profile/job pair.

## Seeding Companies

Seed companies with known career URLs:

```powershell
.\.py312\python.exe scripts\add_companies_seed.py
```

Seed company names from `app/config/companies.seed.json`:

```powershell
.\.py312\python.exe scripts\seed_companies.py
```

You can also add companies from the browser UI. Bulk company input accepts one company per line:

```text
Company Name
Company Name | 9
Company Name | 9 | https://company.example/careers
```

## Browser Workflow

1. Start the server with `.\run.ps1 -Host 127.0.0.1 -Port 8000 -Reload`.
2. Open `http://127.0.0.1:8000/`.
3. Fill in target roles, skills, locations, salary range, experience, and notice period.
4. Upload a CV from the Profile tab.
5. Add or seed target companies.
6. Discover missing career sites if needed.
7. Run a search.
8. Refresh jobs and matches.
9. Review logs from the Logs tab.

## API Reference

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | App health and scheduler status. |
| `GET` | `/profile` | Return the current profile or `null`. |
| `POST` | `/profile` | Create or update the profile. |
| `POST` | `/profile/upload-cv` | Upload and parse a CV file. |
| `GET` | `/companies` | List companies. |
| `POST` | `/companies` | Add or update a company. |
| `POST` | `/companies/discover-career-sites` | Discover missing company career URLs. |
| `POST` | `/search/run` | Run job discovery. Optional `batch_size` query parameter. |
| `GET` | `/jobs` | List stored jobs. |
| `GET` | `/jobs/matches` | Rank stored jobs against the current profile. |
| `POST` | `/jobs/report/email` | Send top-jobs report. Optional `sample=true`. |
| `GET` | `/admin/logs` | Read recent logs. Optional `limit` and `level`. |

Example profile update:

```powershell
$body = @{
  target_roles = @("Data Engineer", "Analytics Engineer")
  skills = @("Python", "SQL", "Spark", "Airflow")
  preferred_locations = @("Bengaluru", "Hyderabad", "Remote")
  remote_preference = "hybrid"
  salary_min = $null
  salary_max = $null
  experience_years = 3
  notice_period_days = 30
  job_level = "mid"
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://127.0.0.1:8000/profile -ContentType "application/json" -Body $body
```

Run a search for up to 10 companies:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/search/run?batch_size=10"
```

Get ranked matches:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs/matches
```

## Scheduler

When `SCHEDULER_ENABLED=true`, APScheduler registers `scheduled_search` at startup and runs it every 12 hours. The scheduled job processes enabled companies with career URLs and uses the configured `SEARCH_BATCH_SIZE`.

Disable it for manual-only operation:

```text
SCHEDULER_ENABLED=false
```

## Logs

Application logs are written to:

```text
logs/oc2.log
```

When using `run.ps1` in the background, server stdout/stderr may also be written to:

```text
logs/server.out.log
logs/server.err.log
```

Recent logs are available from:

```text
http://127.0.0.1:8000/admin/logs
```

Filter by level:

```text
http://127.0.0.1:8000/admin/logs?level=ERROR
```

## Troubleshooting

### PowerShell cannot run scripts

Run the launcher with execution policy bypass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Host 127.0.0.1 -Port 8000 -Reload
```

### Port 8000 is already in use

Use a different port:

```powershell
.\run.ps1 -Host 127.0.0.1 -Port 8001 -Reload
```

### Firecrawl returns no jobs

Check that `FIRECRAWL_API_KEY` is configured, the account has quota, companies have valid `career_url` values, and `SEARCH_ALLOW_SAMPLE_FALLBACK=false` if you only want real jobs.

### Ollama requests fall back

Make sure Ollama is running and the model exists locally:

```powershell
ollama list
ollama pull qwen2.5:3b
```

### Email report fails

Verify SMTP credentials, use a Gmail app password for Gmail, and check `logs/oc2.log` or `/admin/logs?level=ERROR`.

## Development Notes

- The static UI is mounted at `/ui`.
- The root route redirects to `/ui/`.
- SQLAlchemy creates missing tables at startup.
- The app intentionally prefers company career pages and avoids generic scraping of LinkedIn/Indeed job pages.
- Job matching combines deterministic scoring with an Ollama-generated JSON explanation.
