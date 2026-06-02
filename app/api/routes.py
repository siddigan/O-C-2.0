from pathlib import Path
import re

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger, read_recent_logs, setup_logging
from app.core.settings import settings
from app.db.session import get_db
from app.models.models import Company, Job, JobMatch, ManualJobFilter, Profile
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.profile import ProfileCreate, ProfileRead
from app.services.company_service import CompanyService
from app.services.email_service import JobReportEmailService
from app.services.match_service import MatchService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

router = APIRouter()
logger = get_logger(__name__)

FILTERED_JOB_KEYWORDS = ("vice", "lead", "manager", "staff", "senior", "sr")
MAX_VISIBLE_EXPERIENCE_YEARS = 3.0
EXPERIENCE_CONTEXT_TERMS = (
    "experience",
    "experienced",
    "qualification",
    "qualifications",
    "requirement",
    "requirements",
    "minimum",
    "min.",
    "at least",
    "preferred",
)


def _load_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        import json

        parsed = json.loads(value)
    except Exception:
        return []
    return parsed if isinstance(parsed, list) else []


def _experience_requirement(job: Job) -> dict | None:
    text = re.sub(r"\s+", " ", f"{job.title or ''} {job.description or ''}".replace("\xa0", " ")).strip()
    if not text:
        return None

    patterns = [
        re.compile(
            r"\b(?P<min>\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(?P<max>\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\b",
            re.IGNORECASE,
        ),
        re.compile(r"\b(?P<min>\d+(?:\.\d+)?)\s*\+\s*(?:years?|yrs?)\b", re.IGNORECASE),
        re.compile(
            r"\b(?:minimum|min\.?|at least)\s+(?P<min>\d+(?:\.\d+)?)\s*(?:\+)?\s*(?:years?|yrs?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?P<min>\d+(?:\.\d+)?)\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+)?experience\b",
            re.IGNORECASE,
        ),
    ]

    candidates: list[dict] = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            start = max(0, match.start() - 120)
            end = min(len(text), match.end() + 120)
            snippet = text[start:end].strip()
            context = snippet.lower()
            if not any(term in context for term in EXPERIENCE_CONTEXT_TERMS):
                continue

            min_years = float(match.group("min"))
            max_years = float(match.group("max")) if "max" in match.groupdict() and match.group("max") else None
            candidates.append(
                {
                    "min_years": min_years,
                    "max_years": max_years,
                    "snippet": snippet[:260],
                    "confidence": "high",
                    "position": match.start(),
                }
            )

    if not candidates:
        return None

    requirement = sorted(candidates, key=lambda item: item["position"])[0]
    requirement.pop("position", None)
    return requirement


def _filtered_job_reason(job: Job, profile: Profile | None = None, manual_reason: str | None = None) -> str | None:
    if manual_reason:
        return manual_reason

    title = (job.title or "").lower()
    for keyword in FILTERED_JOB_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", title):
            return f"Title contains '{keyword}'"

    requirement = _experience_requirement(job)
    if requirement:
        required_years = float(requirement["min_years"])
        if required_years > MAX_VISIBLE_EXPERIENCE_YEARS:
            required = f"{required_years:g}+ years" if requirement["max_years"] is None else f"{required_years:g}-{requirement['max_years']:g} years"
            profile_text = ""
            if profile and profile.experience_years is not None:
                profile_text = f"; profile has {float(profile.experience_years):g} years"
            return f"Requires {required}; max visible is {MAX_VISIBLE_EXPERIENCE_YEARS:g} years{profile_text}"
    return None


def _job_payload(job: Job, company: Company, profile: Profile | None = None, manual_reason: str | None = None) -> dict:
    reason = _filtered_job_reason(job, profile, manual_reason)
    requirement = _experience_requirement(job)
    return {
        "id": job.id,
        "title": job.title,
        "company": company.name,
        "location": job.location,
        "apply_url": job.apply_url,
        "filtered_out": bool(reason),
        "filtered_reason": reason,
        "experience_required": requirement,
    }


def _manual_filter_map(db: Session) -> dict[int, str]:
    return {item.job_id: item.reason for item in db.query(ManualJobFilter).all()}


def _job_rows(db: Session) -> list[tuple[Job, Company]]:
    return (
        db.query(Job, Company)
        .join(Company, Company.id == Job.company_id)
        .order_by(Company.name.asc(), Job.title.asc())
        .all()
    )


@router.post("/profile", response_model=ProfileRead)
def upsert_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    logger.info("profile.upsert roles=%s skills=%s", len(payload.target_roles), len(payload.skills))
    return ProfileService(db).get_or_create(payload)


@router.get("/profile", response_model=ProfileRead | None)
def get_profile(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    logger.info("profile.fetch found=%s", bool(profile))
    return profile


@router.post("/profile/upload-cv", response_model=ProfileRead)
def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")

    payload = file.file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    profile = db.query(Profile).first() or Profile()
    db.add(profile)
    db.commit()
    db.refresh(profile)

    Path("data/cv").mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename).name
    path = Path("data/cv") / safe_name
    path.write_bytes(payload)

    logger.info(
        "profile.upload_cv filename=%s bytes=%s content_type=%s",
        safe_name,
        len(payload),
        file.content_type or "unknown",
    )

    return ProfileService(db).parse_cv(profile, str(path))


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    companies = CompanyService(db).list_companies()
    logger.info("companies.list count=%s", len(companies))
    return companies


@router.post("/companies", response_model=CompanyRead)
def add_company(payload: CompanyCreate, db: Session = Depends(get_db)):
    logger.info("companies.upsert name=%s priority=%s", payload.name, payload.priority)
    return CompanyService(db).add_company(payload)


@router.post("/companies/discover-career-sites")
def discover_career_sites(db: Session = Depends(get_db)):
    logger.info("companies.discover_missing.start")
    return CompanyService(db).discover_missing_career_sites()


@router.post("/search/run")
def run_search(
    batch_size: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
):
    logger.info("search.run.start batch_size=%s", batch_size)
    return SearchService(db).run_cycle(batch_size=batch_size)


@router.post("/jobs/report/email")
def send_jobs_report(
    sample: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    logger.info("jobs.report.email.start sample=%s", sample)
    service = JobReportEmailService(db)
    return service.send_sample_email() if sample else service.send_top_jobs_report(limit=15)


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    manual_filters = _manual_filter_map(db)
    jobs = [_job_payload(job, company, profile, manual_filters.get(job.id)) for job, company in _job_rows(db)]
    visible_jobs = [job for job in jobs if not job["filtered_out"]]
    logger.info("jobs.list count=%s visible=%s filtered=%s", len(jobs), len(visible_jobs), len(jobs) - len(visible_jobs))
    return visible_jobs


@router.get("/jobs/filtered-out")
def list_filtered_out_jobs(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    manual_filters = _manual_filter_map(db)
    jobs = [_job_payload(job, company, profile, manual_filters.get(job.id)) for job, company in _job_rows(db)]
    filtered_jobs = [job for job in jobs if job["filtered_out"]]
    logger.info("jobs.filtered_out.list count=%s keywords=%s", len(filtered_jobs), ",".join(FILTERED_JOB_KEYWORDS))
    return {
        "keywords": FILTERED_JOB_KEYWORDS,
        "max_visible_experience_years": MAX_VISIBLE_EXPERIENCE_YEARS,
        "profile_experience_years": profile.experience_years if profile else None,
        "jobs": filtered_jobs,
    }


@router.post("/jobs/{job_id}/filter")
def move_job_to_filtered(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    item = db.query(ManualJobFilter).filter(ManualJobFilter.job_id == job_id).first()
    if not item:
        item = ManualJobFilter(job_id=job_id, reason="Moved manually")
        db.add(item)
    else:
        item.reason = "Moved manually"
    db.commit()
    logger.info("jobs.filter.manual job_id=%s title=%s", job.id, job.title)
    return {"job_id": job_id, "filtered": True, "reason": item.reason}


@router.get("/jobs/matches")
def rank_jobs(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        logger.info("jobs.matches skipped=no_profile")
        return []

    matcher = MatchService()
    output = []
    manual_filters = _manual_filter_map(db)
    jobs = [(job, company) for job, company in _job_rows(db) if not _filtered_job_reason(job, profile, manual_filters.get(job.id))]

    logger.info("jobs.matches.start jobs=%s", len(jobs))

    for job, company in jobs:
        score, reason, missing = matcher.score(profile, job, company.priority)
        fit_level = "high" if score >= 75 else "medium" if score >= 55 else "low"
        db.add(
            JobMatch(
                profile_id=profile.id,
                job_id=job.id,
                match_score=score,
                fit_level=fit_level,
                missing_skills=missing,
                match_reason=reason,
                rank_score=score,
            )
        )
        output.append(
            {
                "job_id": job.id,
                "company": company.name,
                "score": score,
                "fit_level": fit_level,
                "reason": reason,
            }
        )
    db.commit()

    logger.info("jobs.matches.complete generated=%s", len(output))
    return sorted(output, key=lambda item: item["score"], reverse=True)


@router.get("/admin/db")
def get_database_overview(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    companies = db.query(Company).order_by(Company.priority.desc(), Company.name.asc()).all()
    job_rows = _job_rows(db)
    manual_filters = _manual_filter_map(db)
    jobs = [_job_payload(job, company, profile, manual_filters.get(job.id)) for job, company in job_rows]
    matches = (
        db.query(JobMatch, Job, Company)
        .join(Job, Job.id == JobMatch.job_id)
        .join(Company, Company.id == Job.company_id)
        .order_by(JobMatch.rank_score.desc(), JobMatch.created_at.desc())
        .limit(50)
        .all()
    )

    filtered_jobs = [job for job in jobs if job["filtered_out"]]
    visible_jobs = [job for job in jobs if not job["filtered_out"]]

    return {
        "counts": {
            "profiles": 1 if profile else 0,
            "companies": len(companies),
            "enabled_companies": len([company for company in companies if company.enabled]),
            "jobs": len(jobs),
            "visible_jobs": len(visible_jobs),
            "filtered_jobs": len(filtered_jobs),
            "manual_filters": len(manual_filters),
            "matches": db.query(JobMatch).count(),
        },
        "profile": None
        if not profile
        else {
            "id": profile.id,
            "target_roles": _load_json_list(profile.target_roles),
            "skills": _load_json_list(profile.skills),
            "preferred_locations": _load_json_list(profile.preferred_locations),
            "remote_preference": profile.remote_preference,
            "experience_years": profile.experience_years,
            "notice_period_days": profile.notice_period_days,
            "job_level": profile.job_level,
            "cv_path": profile.cv_path,
            "profile_summary": profile.profile_summary,
            "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        },
        "companies": [
            {
                "id": company.id,
                "name": company.name,
                "priority": company.priority,
                "enabled": company.enabled,
                "career_url": company.career_url,
            }
            for company in companies[:100]
        ],
        "jobs": visible_jobs[:100],
        "filtered_jobs": filtered_jobs[:100],
        "matches": [
            {
                "id": match.id,
                "job_id": job.id,
                "title": job.title,
                "company": company.name,
                "score": match.match_score,
                "fit_level": match.fit_level,
                "missing_skills": _load_json_list(match.missing_skills),
                "reason": match.match_reason,
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }
            for match, job, company in matches
        ],
        "filter_keywords": FILTERED_JOB_KEYWORDS,
        "max_visible_experience_years": MAX_VISIBLE_EXPERIENCE_YEARS,
    }


@router.get("/admin/logs")
def get_logs(
    limit: int = Query(default=200, ge=1, le=500),
    level: str | None = Query(default=None),
):
    log_entries = read_recent_logs(limit=limit, level=level)
    return {
        "log_file": settings.log_file,
        "entries": log_entries,
        "count": len(log_entries),
        "available": Path(setup_logging()).exists(),
    }
