import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.models import Profile
from app.schemas.profile import ProfileCreate
from app.services.ollama_client import OllamaClient


class ProfileService:
    def __init__(self, db: Session):
        self.db = db
        self.ollama = OllamaClient()

    def get_or_create(self, payload: ProfileCreate) -> Profile:
        profile = self.db.query(Profile).first() or Profile()
        profile.target_roles = json.dumps(payload.target_roles)
        profile.skills = json.dumps(payload.skills)
        profile.preferred_locations = json.dumps(payload.preferred_locations)
        profile.remote_preference = payload.remote_preference
        profile.salary_min = payload.salary_min
        profile.salary_max = payload.salary_max
        profile.experience_years = payload.experience_years
        profile.notice_period_days = payload.notice_period_days
        profile.job_level = payload.job_level
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def parse_cv(self, profile: Profile, cv_path: str) -> Profile:
        text = Path(cv_path).read_text(encoding="utf-8", errors="ignore")[:12000]
        prompt = (
            "Extract candidate profile JSON with skills, target_roles, preferred_locations, profile_summary."
            f"\nResume:\n{text}"
        )
        parsed = self.ollama.chat_json(prompt, fallback={"profile_summary": "CV parsed locally."})
        profile.cv_path = cv_path
        profile.profile_summary = parsed.get("profile_summary", "CV parsed locally.")
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile
