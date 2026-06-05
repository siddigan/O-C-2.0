# OC2 Local Job Search

OC2 is a local job-search dashboard for maintaining target companies, discovering roles from company career pages, filtering out poor-fit roles, ranking visible jobs against a profile, and preparing short referral messages.

The app is designed for one local user and a focused company list. It uses FastAPI, SQLite, a static browser UI, Firecrawl for discovery, and Ollama for CV parsing and match explanations.

## Current Features

- Create and update a job-search profile.
- Upload a CV and store a parsed profile summary.
- Maintain prioritized target companies and career URLs.
- Discover missing company career-site URLs.
- Run job discovery manually or through the scheduler.
- Store all discovered jobs in SQLite with dedupe checks.
- Split jobs into visible jobs and filtered-out jobs after discovery.
- Filter by seniority/title keywords: `vice`, `lead`, `manager`, `staff`, `senior`, `sr`.
- Filter clear experience requirements above `3` years, such as `4+`, `5-7`, `6+`, or `8-12 years`.
- Manually move any visible job into Filtered Out Jobs.
- Expand a visible job row to show:
  - detected experience requirement
  - location
  - short LinkedIn referral message customized with job title/company
  - copy-message button
  - move-to-filtered button
- Rank visible jobs against the current profile.
- View formatted database contents in the Admin tab.
- View backend and UI logs in the Logs tab.
- Send top-job email reports when SMTP is configured.
- Launch from a Windows desktop shortcut without opening VS Code.
- Uses OC2 logo assets for the desktop shortcut and browser tab icon.

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
  api/routes.py             API routes, job filtering, admin DB overview
  core/settings.py          Environment-backed configuration
  core/logging_config.py    File and console logging
  db/session.py             SQLAlchemy engine/session setup
  models/models.py          Profile, Company, Job, JobMatch, ManualJobFilter tables
  services/                 Profile, company, search, match, email services
frontend/
  assets/                   OC2 logo SVG/PNG/ICO
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
start_oc2_ui.ps1            Starts server and opens browser UI
```

## Quick Start

From PowerShell in the project root:

```powershell
.\run.ps1 -Host 127.0.0.1 -Port 8000 -Reload
```

Open:

```text
http://127.0.0.1:8000/
```

The root path redirects to `/ui/`.

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok","scheduler_enabled":true}
```

## Desktop Shortcut

The launcher script is:

```powershell
.\start_oc2_ui.ps1
```

It starts the server in the background, waits for `/health`, and opens the UI in the default browser.

The desktop shortcut created for this workspace is:

```text
C:\Users\siddi\OneDrive\Desktop\OC2.lnk
```

The shortcut uses:

```text
frontend/assets/oc2-logo.ico
```

If Windows shows an older icon, refresh the desktop or restart Explorer.

## Setup From Scratch

This repository includes a local `.py312` Python runtime and `run.ps1` uses it automatically.

If you want to use your own virtual environment:

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

Copy `.env.example` to `.env`:

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

PowerShell session-only Firecrawl key syntax:

```powershell
$env:FIRECRAWL_API_KEY="your-key"
```

For normal app use, put the key in `.env` and restart the server.

## Firecrawl

Firecrawl is used by `SearchService` to search company career domains and scrape markdown content.

Plain `.env` key:

```text
FIRECRAWL_API_KEY="your-key"
```

Encrypted key flow:

```powershell
.\.py312\python.exe scripts\encrypt_secret.py
```

Then paste the generated values into `.env`:

```text
FIRECRAWL_SECRET_KEY="..."
FIRECRAWL_API_KEY_ENCRYPTED="..."
```

If logs show `firecrawl.search.skipped reason=missing_api_key`, either `.env` is missing, the key is empty, or the running server was started before the key was added. Restart the server after updating `.env`.

## Ollama

Install and start Ollama separately:

```powershell
ollama pull qwen2.5:3b
ollama serve
```

If Ollama is not running, match explanations fall back to defaults. The app still works, but match refresh can be slower because the request waits for the Ollama connection attempt to fail.

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

Send a sample report:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/jobs/report/email?sample=true"
```

If `SMTP_PASSWORD` is missing, reports are skipped with `missing_smtp_password`.

## Database

The default database is:

```text
oc2.db
```

Tables are created automatically at startup.

Main tables:

- `profiles`: current user profile and CV summary.
- `companies`: target companies, priority, enabled flag, and career URL.
- `jobs`: discovered jobs with description, apply URL, hash, and source confidence.
- `job_matches`: generated ranking results.
- `manual_job_filters`: jobs manually moved to Filtered Out Jobs.

## Job Filtering

Filtering is post-processing. The app keeps all discovered jobs in the DB, then separates them for display.

Visible jobs are returned from:

```text
GET /jobs
```

Filtered jobs are returned from:

```text
GET /jobs/filtered-out
```

Automatic filter rules:

- Title contains `vice`, `lead`, `manager`, `staff`, `senior`, or `sr`.
- Clear minimum experience is above `3` years.

Examples filtered by experience:

```text
4+ years
4-8 years
5+ years
5-7 years
6+ years
8-12 years
```

Examples kept visible:

```text
2-4 years
2-5 years
3 years
Experience not detected
```

Manual filter:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/jobs/71/filter"
```

The dashboard exposes this as **Move to Filtered Out Jobs** inside an expanded visible job row.

## Browser Workflow

1. Start the server or use the `OC2.lnk` desktop shortcut.
2. Open `http://127.0.0.1:8000/`.
3. Fill in profile roles, skills, locations, salary range, experience, and notice period.
4. Upload a CV from the Admin tab.
5. Add or seed target companies.
6. Discover missing career sites if needed.
7. Run Search Cycle.
8. Review visible jobs and Filtered Out Jobs.
9. Click a visible job row to expand it.
10. Copy the LinkedIn referral message or move the job to Filtered Out Jobs.
11. Refresh or generate matches.
12. Use Admin > Database Contents to inspect stored data.
13. Use Logs to debug search, Firecrawl, Ollama, SMTP, and UI activity.

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
| `GET` | `/jobs` | List visible jobs after filtering. |
| `GET` | `/jobs/filtered-out` | List filtered jobs and filter metadata. |
| `POST` | `/jobs/{job_id}/filter` | Manually move a job to Filtered Out Jobs. |
| `GET` | `/jobs/matches` | Rank visible jobs against the current profile. |
| `POST` | `/jobs/report/email` | Send top-jobs report. Optional `sample=true`. |
| `GET` | `/admin/db` | Formatted DB overview for the Admin tab. |
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
  experience_years = 2
  notice_period_days = 30
  job_level = "entry"
} | ConvertTo-Json

Invoke-RestMethod -Method Post http://127.0.0.1:8000/profile -ContentType "application/json" -Body $body
```

Run a small search:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/search/run?batch_size=1"
```

Run a larger search:

```powershell
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/search/run?batch_size=10"
```

Get visible jobs:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs
```

Get filtered jobs:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs/filtered-out
```

Get ranked matches:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/jobs/matches
```

## Seeding Companies

Seed companies with known career URLs:

```powershell
.\.py312\python.exe scripts\add_companies_seed.py
```

This seed includes a priority-10 quant and hedge-fund set: Jane Street, Citadel, Citadel Securities, Hudson River Trading, Two Sigma, D.E. Shaw, Jump Trading, Optiver, IMC Trading, DRW, SIG, Five Rings, Akuna, Millennium, Point72, Balyasny, Bridgewater, Schonfeld, Squarepoint, Qube Research & Technologies, G-Research, and XTX Markets.

Seed company names from `app/config/companies.seed.json`:

```powershell
.\.py312\python.exe scripts\seed_companies.py
```

Bulk company input in the UI accepts:

```text
Company Name
Company Name | 9
Company Name | 9 | https://company.example/careers
```

## Scheduler

When `SCHEDULER_ENABLED=true`, APScheduler registers a background search job at startup and runs it every 12 hours.

Disable scheduled search:

```text
SCHEDULER_ENABLED=false
```

Manual search still works when the scheduler is disabled.

## Logs

Application log:

```text
logs/oc2.log
```

Background server logs:

```text
logs/server.out.log
logs/server.err.log
```

Recent logs:

```text
http://127.0.0.1:8000/admin/logs
```

Filter by level:

```text
http://127.0.0.1:8000/admin/logs?level=ERROR
```

## Troubleshooting

### PowerShell cannot run scripts

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1 -Host 127.0.0.1 -Port 8000 -Reload
```

### Port 8000 is already in use

```powershell
.\run.ps1 -Host 127.0.0.1 -Port 8001 -Reload
```

### Firecrawl says missing API key

1. Confirm `.env` exists.
2. Confirm `FIRECRAWL_API_KEY` is not empty.
3. Restart the server after editing `.env`.

### Firecrawl finds no jobs

Check API quota, company career URLs, `FIRECRAWL_COUNTRY`, `FIRECRAWL_LOCATION`, and `FIRECRAWL_LOCATION_TERMS`.

### Run Search Cycle inserts zero jobs

This can be normal if every result already exists, is outside the company domain, is irrelevant to target roles, or is filtered by the search service before insertion. Check `logs/oc2.log` for `firecrawl.search.complete`, `search.job.created`, `search.job.skipped`, and `filtered_irrelevant`.

### Ollama requests fall back

```powershell
ollama list
ollama pull qwen2.5:3b
ollama serve
```

### Email report fails

Verify SMTP credentials and check `logs/oc2.log` or `/admin/logs?level=ERROR`.

## Development Notes

- Static UI is mounted at `/ui`.
- Root route redirects to `/ui/`.
- SQLAlchemy creates missing tables at startup.
- Search prefers company career domains and avoids LinkedIn/Indeed scraping paths.
- Filtering is display-time post-processing; discovered jobs remain stored.
- Manual filtering is persisted in `manual_job_filters`.
- Job matching ranks only visible jobs.
