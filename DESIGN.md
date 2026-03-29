# OC2 Lightweight, Configuration-Driven Architecture

## Product outcome
A local-first personalized job search system that:
1. Stores user profile + CV.
2. Tracks curated target companies (40-50+).
3. Searches company-approved public sources on schedule.
4. Extracts + normalizes jobs with Qwen via Ollama.
5. Ranks jobs with deterministic + LLM explanation.

## Design principles
- **Small footprint:** FastAPI + SQLite + APScheduler.
- **Config driven:** company sources live in data/config, not hardcoded crawlers.
- **LLM where useful:** parse/normalize/explain/rerank, not everything.
- **Resilient:** retries, per-domain throttling, source confidence + fallbacks.

## Pipeline
1. Profile setup + CV upload.
2. Qwen resume parser creates normalized profile summary.
3. Scheduler enqueues company-source batches (5 companies per cycle).
4. Fetchers pull official career pages first, then allowed fallbacks.
5. Parser converts HTML to text and Qwen returns strict JSON job schema.
6. Dedup by `company + title + location + apply_url` hash.
7. Match engine computes deterministic score and Qwen explanation.
8. Dashboard shows ranked jobs, fit level, missing skills, and apply URL.

## Deterministic scoring (default)
```text
final_score =
  0.35 * skills_overlap
+ 0.20 * role_match
+ 0.15 * location_match
+ 0.10 * seniority_match
+ 0.10 * company_priority
+ 0.10 * semantic_similarity
```

## Modules in this scaffold
- `ProfileService`: CRUD + CV parsing hook to Ollama.
- `CompanyService`: list companies + discovery status.
- `SearchService`: batch-cycle orchestrator stub.
- `MatchService`: deterministic rank + Qwen reason JSON.
- `scripts/seed_companies.py`: loads your long company list.
- `scripts/discover_career_sites.py`: best-effort internet lookup for missing career URLs.

## Why this works for 40-50 companies
- Batch processing avoids request spikes.
- SQLite remains enough for single-user local execution.
- Config-first source setup makes it maintainable when company pages change.
- Playwright stays optional to keep memory low.
