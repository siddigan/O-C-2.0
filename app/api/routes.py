from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger, read_recent_logs, setup_logging
from app.core.settings import settings
from app.db.session import get_db
from app.models.models import Company, Job, JobMatch, Profile
from app.schemas.company import CompanyCreate, CompanyRead
from app.schemas.profile import ProfileCreate, ProfileRead
from app.services.company_service import CompanyService
from app.services.email_service import JobReportEmailService
from app.services.match_service import MatchService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

router = APIRouter()
logger = get_logger(__name__)


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
    jobs = (
        db.query(Job, Company)
        .join(Company, Company.id == Job.company_id)
        .order_by(Company.name.asc(), Job.title.asc())
        .all()
    )
    logger.info("jobs.list count=%s", len(jobs))
    return [
        {
            "id": job.id,
            "title": job.title,
            "company": company.name,
            "location": job.location,
            "apply_url": job.apply_url,
        }
        for job, company in jobs
    ]


@router.get("/jobs/matches")
def rank_jobs(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        logger.info("jobs.matches skipped=no_profile")
        return []

    matcher = MatchService()
    output = []
    jobs = db.query(Job, Company).join(Company, Company.id == Job.company_id).all()

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
