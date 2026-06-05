# OC2 Design And User Workflow

## Product Goal

OC2 is a local job-search control room for one user. It helps the user maintain a focused target-company list, discover relevant jobs from official career pages, hide poor-fit roles, review visible jobs, copy referral messages, and inspect all stored data without leaving the browser.

The app is intentionally local-first in operation: profile data, discovered jobs, manual filters, matches, logs, and CV files are stored on the user's machine.

## Target User

The primary user is a job seeker focused on data engineering roles across a curated list of companies. The user wants to reduce repeated manual checking of career pages, avoid senior/manager roles that are not realistic, and quickly act on suitable roles with referral outreach.

## User Outcomes

1. Keep one accurate job-search profile.
2. Maintain a prioritized list of target companies.
3. Discover roles from company career sites.
4. Automatically hide roles that are too senior or require more than 3 years of experience.
5. Manually hide roles that are not useful.
6. Expand a job to copy a short LinkedIn referral message.
7. Rank visible jobs against profile skills and target roles.
8. View database contents and logs in a user-friendly way.

## Main Screens

### Dashboard

The Dashboard is the working surface for the job search.

It includes:

- Status panel.
- Run Search Cycle button.
- Refresh Jobs button.
- Re-rank button.
- Email Top 15 button.
- Visible Jobs table.
- Filtered Out Jobs table.
- Matches section.

Visible job rows are expandable. When selected, a job opens inline below the row and shows:

- detected experience requirement, if available
- job location, if available
- short LinkedIn referral message
- Copy Message button
- Move to Filtered Out Jobs button

### Admin

The Admin tab contains setup and database inspection.

It includes:

- profile form
- CV upload
- company list
- career-site discovery controls
- bulk company add
- formatted Database Contents panel

The Database Contents panel shows:

- profile summary
- counts for profiles, companies, jobs, visible jobs, filtered jobs, manual filters, and matches
- company records
- visible jobs
- filtered jobs
- recent matches

### Logs

The Logs tab gives operational visibility.

It includes:

- server log entries
- UI log entries
- level filter
- manual refresh
- auto-refresh toggle

This is used to debug Firecrawl, search filtering, Ollama fallbacks, SMTP, and frontend actions.

## Core Workflow

### First-Time Setup

1. Launch OC2 from the desktop shortcut or with `run.ps1`.
2. Open `http://127.0.0.1:8000/`.
3. Go to Admin.
4. Fill profile details:
   - target roles
   - skills
   - preferred locations
   - remote preference
   - salary range
   - experience years
   - notice period
   - job level
5. Upload CV.
6. Add target companies or seed companies from scripts.
7. Configure Firecrawl in `.env`.
8. Restart the server after editing `.env`.

### Daily Search Workflow

1. Open OC2.
2. Click Run Search Cycle.
3. Review the visible Jobs table.
4. Review Filtered Out Jobs to confirm the filter behavior.
5. Expand promising visible jobs.
6. Copy the LinkedIn referral message.
7. Open the job apply URL.
8. Move irrelevant visible jobs to Filtered Out Jobs.
9. Click Re-rank if new visible jobs were added.
10. Check Logs if search results seem wrong.

### Referral Workflow

1. Click a visible job row.
2. Read the inline job detail panel.
3. Copy the generated LinkedIn referral message.
4. Paste it into LinkedIn.
5. Edit the message if needed.
6. Open the job link and apply.

The referral message is intentionally short. It includes:

- job title
- company name
- user's data engineering background
- polite referral request

### Manual Filtering Workflow

1. Click a visible job row.
2. Click Move to Filtered Out Jobs.
3. The job is persisted in `manual_job_filters`.
4. The job disappears from visible jobs.
5. The job appears in Filtered Out Jobs with reason `Moved manually`.

## Filtering Design

Filtering is display-time post-processing. The app keeps every discovered job in the `jobs` table, then separates jobs into visible and filtered groups for UI/API responses.

### Automatic Title Filters

Jobs are filtered out if the title contains:

```text
vice
lead
manager
staff
senior
sr
```

This catches roles that are usually too senior even when the scraped job description does not expose years of experience.

### Experience Requirement Filters

The app scans stored job descriptions for clear experience requirements.

Filtered examples:

```text
4+ years
4-8 years
5+ years
5-7 years
6+ years
8-12 years
```

Kept visible:

```text
2-4 years
2-5 years
3 years
Experience not detected
```

The current threshold is:

```text
MAX_VISIBLE_EXPERIENCE_YEARS = 3.0
```

The filter is conservative for unclear pages. If no clear experience requirement is detected, the job stays visible unless a title keyword or manual filter applies.

## Data Model

### `profiles`

Stores the user's search profile:

- target roles
- skills
- preferred locations
- remote preference
- salary range
- experience years
- notice period
- job level
- CV path
- parsed profile summary

### `companies`

Stores target companies:

- name
- priority
- enabled flag
- career URL
- metadata JSON

Top quant trading and hedge-fund firms are seeded at priority 10 so they are processed before the general priority-9 target list. The priority-10 set includes Jane Street, Citadel, Citadel Securities, Hudson River Trading, Two Sigma, D.E. Shaw, Jump Trading, Optiver, IMC Trading, DRW, SIG, Five Rings, Akuna, Millennium, Point72, Balyasny, Bridgewater, Schonfeld, Squarepoint, Qube Research & Technologies, G-Research, and XTX Markets.

### `jobs`

Stores discovered jobs:

- company ID
- title
- location
- description
- apply URL
- posted date
- dedupe hash
- source confidence

### `job_matches`

Stores generated match results:

- profile ID
- job ID
- match score
- fit level
- missing skills
- match reason
- rank score

### `manual_job_filters`

Stores jobs manually moved to Filtered Out Jobs:

- job ID
- reason
- created timestamp

## Search Pipeline

1. User clicks Run Search Cycle or scheduler triggers search.
2. `SearchService` selects enabled companies with career URLs.
3. Firecrawl searches the company career domain.
4. Search results are screened for:
   - valid job URL shape
   - company domain ownership
   - relevant data-role title/text
   - India/location relevance
5. Jobs are inserted if not duplicates.
6. Email report is attempted if configured.
7. UI refreshes visible jobs, filtered jobs, matches, and DB overview.

## Matching Pipeline

1. User clicks Re-rank or page initialization loads matches.
2. App loads current profile.
3. App loads visible jobs only.
4. `MatchService` computes deterministic score:

```text
final_score =
  0.35 * skills_overlap
+ 0.20 * role_match
+ 0.15 * location_match
+ 0.10 * seniority_match
+ 0.10 * company_priority
+ 0.10 * keyword_similarity
```

5. Ollama is asked for concise JSON explanation.
6. If Ollama is unavailable, fallback explanation is used.
7. Matches are stored in `job_matches`.

## API Surface

| Method | Path | User Purpose |
| --- | --- | --- |
| `GET` | `/health` | Confirm server is running. |
| `GET` | `/profile` | Load profile into Admin form. |
| `POST` | `/profile` | Save profile. |
| `POST` | `/profile/upload-cv` | Upload and parse CV. |
| `GET` | `/companies` | Load target company list. |
| `POST` | `/companies` | Add/update company. |
| `POST` | `/companies/discover-career-sites` | Discover missing career URLs. |
| `POST` | `/search/run` | Run job discovery. |
| `GET` | `/jobs` | Load visible jobs. |
| `GET` | `/jobs/filtered-out` | Load filtered jobs. |
| `POST` | `/jobs/{job_id}/filter` | Manually filter a job. |
| `GET` | `/jobs/matches` | Rank visible jobs. |
| `POST` | `/jobs/report/email` | Send top jobs by email. |
| `GET` | `/admin/db` | Load formatted database overview. |
| `GET` | `/admin/logs` | Load recent logs. |

## Accessibility And Usability

Current usability choices:

- Browser UI launches from desktop shortcut.
- Visible and filtered jobs are separated.
- Job rows expand inline instead of opening a separate page.
- Referral message can be copied with one button.
- Logs are visible from the UI.
- Admin DB contents are formatted instead of shown as raw JSON.

Recommended future improvements:

- Add application status: Interested, Applied, Referral Asked, Interview, Rejected.
- Add notes per job.
- Add follow-up reminders.
- Add filters by company, location, match score, remote/hybrid, and posted date.
- Add CSV/Excel export.
- Add undo for manual filtering.
- Add keyboard shortcuts for expanding jobs and copying messages.
- Add a compact mobile layout.
- Add color contrast and focus-state audit.

## Operating Assumptions

- The app is used by one person locally.
- SQLite is sufficient for current scale.
- Company career pages are preferred over job aggregator scraping.
- Firecrawl may return irrelevant or duplicate results, so post-processing is required.
- Some job descriptions do not expose years of experience, so filtering must remain conservative.
- Ollama is optional for basic operation but improves profile parsing and match explanations.

## Non-Goals

- Multi-user authentication.
- Cloud deployment.
- Scraping LinkedIn or Indeed job pages.
- Full applicant tracking system.
- Automatic job application submission.

## Quality Checks

Before relying on the daily workflow:

1. Confirm `/health` returns `ok`.
2. Confirm `.env` contains a Firecrawl key.
3. Run `POST /search/run?batch_size=1`.
4. Confirm jobs are inserted or existing jobs are skipped intentionally.
5. Confirm visible jobs do not contain obvious senior roles.
6. Confirm filtered jobs include senior and high-experience roles.
7. Confirm logs do not show Firecrawl quota or missing-key errors.
