import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Company, Job, JobMatch, Profile
from app.schemas.company import CompanyRead
from app.schemas.profile import ProfileCreate, ProfileRead
from app.services.company_service import CompanyService
from app.services.match_service import MatchService
from app.services.profile_service import ProfileService
from app.services.search_service import SearchService

router = APIRouter()


@router.post("/profile", response_model=ProfileRead)
def upsert_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    return ProfileService(db).get_or_create(payload)


@router.get("/profile", response_model=ProfileRead | None)
def get_profile(db: Session = Depends(get_db)):
    return db.query(Profile).first()


@router.post("/profile/upload-cv", response_model=ProfileRead)
def upload_cv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = db.query(Profile).first() or Profile()
    db.add(profile)
    db.commit()
    db.refresh(profile)

    Path("data/cv").mkdir(parents=True, exist_ok=True)
    path = Path("data/cv") / file.filename
    path.write_bytes(file.file.read())
    return ProfileService(db).parse_cv(profile, str(path))


@router.get("/companies", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)):
    return CompanyService(db).list_companies()


@router.post("/companies/discover-career-sites")
def discover_career_sites(db: Session = Depends(get_db)):
    return CompanyService(db).discover_missing_career_sites()


@router.post("/search/run")
def run_search(db: Session = Depends(get_db)):
    return SearchService(db).run_cycle()


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    return [{"id": j.id, "title": j.title, "apply_url": j.apply_url} for j in jobs]


@router.get("/jobs/matches")
def rank_jobs(db: Session = Depends(get_db)):
    profile = db.query(Profile).first()
    if not profile:
        return []
    matcher = MatchService()
    output = []
    jobs = db.query(Job, Company).join(Company, Company.id == Job.company_id).all()
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
        output.append({"job_id": job.id, "company": company.name, "score": score, "fit_level": fit_level, "reason": reason})
    db.commit()
    return sorted(output, key=lambda x: x["score"], reverse=True)
