import hashlib

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.models import Company, Job

logger = get_logger(__name__)


class SearchService:
    def __init__(self, db: Session):
        self.db = db

    def run_cycle(self, batch_size: int = 5) -> dict:
        companies = (
            self.db.query(Company)
            .filter(Company.enabled.is_(True), Company.career_url.is_not(None))
            .order_by(Company.priority.desc())
            .limit(batch_size)
            .all()
        )

        logger.info("search.run_cycle.start batch_size=%s companies=%s", batch_size, len(companies))

        discovered = 0
        for company in companies:
            title = f"Sample {company.name} Role"
            apply_url = f"{company.career_url.rstrip('/')}/sample-role"
            job_hash = hashlib.sha1(f"{company.name}|{title}|{apply_url}".encode()).hexdigest()
            exists = self.db.query(Job).filter(Job.job_hash == job_hash).first()
            if exists:
                logger.info("search.job.skipped company=%s reason=existing_hash", company.name)
                continue

            self.db.add(
                Job(
                    company_id=company.id,
                    title=title,
                    location="Remote",
                    description="Placeholder extracted job content for MVP pipeline wiring.",
                    apply_url=apply_url,
                    job_hash=job_hash,
                    source_confidence=0.35,
                )
            )
            discovered += 1
            logger.info("search.job.created company=%s apply_url=%s", company.name, apply_url)

        self.db.commit()
        result = {"companies_processed": len(companies), "jobs_inserted": discovered}
        logger.info("search.run_cycle.complete companies=%s jobs_inserted=%s", len(companies), discovered)
        return result
