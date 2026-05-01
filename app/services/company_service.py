from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.models import Company

logger = get_logger(__name__)


class CompanyService:
    def __init__(self, db: Session):
        self.db = db

    def list_companies(self) -> list[Company]:
        companies = self.db.query(Company).order_by(Company.priority.desc(), Company.name.asc()).all()
        logger.info("company.list count=%s", len(companies))
        return companies

    def add_company(self, payload) -> Company:
        existing = self.db.query(Company).filter(Company.name == payload.name).first()
        if existing:
            existing.priority = payload.priority
            existing.enabled = payload.enabled
            existing.career_url = payload.career_url
            self.db.commit()
            self.db.refresh(existing)
            logger.info("company.updated name=%s priority=%s", existing.name, existing.priority)
            return existing

        company = Company(
            name=payload.name,
            priority=payload.priority,
            enabled=payload.enabled,
            career_url=payload.career_url,
        )
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        logger.info("company.created name=%s priority=%s", company.name, company.priority)
        return company

    def discover_missing_career_sites(self) -> dict:
        missing = self.db.query(Company).filter(Company.career_url.is_(None)).count()
        logger.info("company.discover_missing count=%s", missing)
        return {"missing_career_urls": missing, "note": "Run scripts/discover_career_sites.py for web lookup."}
