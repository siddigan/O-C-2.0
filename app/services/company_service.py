from sqlalchemy.orm import Session

from app.models.models import Company


class CompanyService:
    def __init__(self, db: Session):
        self.db = db

    def list_companies(self) -> list[Company]:
        return self.db.query(Company).order_by(Company.priority.desc(), Company.name.asc()).all()

    def discover_missing_career_sites(self) -> dict:
        # Placeholder hook: keep config-driven and optional internet discovery in script.
        missing = self.db.query(Company).filter(Company.career_url.is_(None)).count()
        return {"missing_career_urls": missing, "note": "Run scripts/discover_career_sites.py for web lookup."}
