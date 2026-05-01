import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.models.models import Profile
from app.schemas.profile import ProfileCreate
from app.services.ollama_client import OllamaClient

logger = get_logger(__name__)


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

        logger.info(
            "profile.saved id=%s roles=%s skills=%s locations=%s",
            profile.id,
            len(payload.target_roles),
            len(payload.skills),
            len(payload.preferred_locations),
        )
        return profile

    def parse_cv(self, profile: Profile, cv_path: str) -> Profile:
        path = Path(cv_path)
        extracted_text = self._extract_text(path)

        logger.info(
            "profile.parse_cv.start id=%s path=%s chars=%s",
            profile.id,
            str(path),
            len(extracted_text),
        )

        prompt = (
            "Extract candidate profile JSON with keys skills, target_roles, preferred_locations, profile_summary. "
            "Each list must be an array of strings."
            f"\nResume:\n{extracted_text[:12000]}"
        )
        parsed = self.ollama.chat_json(
            prompt,
            fallback={
                "skills": self._load_list(profile.skills),
                "target_roles": self._load_list(profile.target_roles),
                "preferred_locations": self._load_list(profile.preferred_locations),
                "profile_summary": "CV uploaded. Structured parsing fell back to local defaults.",
            },
        )

        profile.cv_path = cv_path
        profile.skills = json.dumps(self._normalize_list(parsed.get("skills"), self._load_list(profile.skills)))
        profile.target_roles = json.dumps(
            self._normalize_list(parsed.get("target_roles"), self._load_list(profile.target_roles))
        )
        profile.preferred_locations = json.dumps(
            self._normalize_list(parsed.get("preferred_locations"), self._load_list(profile.preferred_locations))
        )
        profile.profile_summary = parsed.get("profile_summary") or "CV uploaded and processed."

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        logger.info(
            "profile.parse_cv.complete id=%s skills=%s roles=%s locations=%s",
            profile.id,
            len(self._load_list(profile.skills)),
            len(self._load_list(profile.target_roles)),
            len(self._load_list(profile.preferred_locations)),
        )
        return profile

    def _extract_text(self, path: Path) -> str:
        raw_bytes = path.read_bytes()
        suffix = path.suffix.lower()

        if suffix in {".txt", ".md", ".json"}:
            return raw_bytes.decode("utf-8", errors="ignore")

        decoded = raw_bytes.decode("utf-8", errors="ignore")
        compact = " ".join(decoded.split())

        if len(compact) >= 80:
            return compact

        logger.warning("profile.parse_cv.limited_extraction path=%s suffix=%s", str(path), suffix or "none")
        return (
            f"Uploaded resume file named {path.name}. "
            f"Automatic text extraction is limited for {suffix or 'this'} format in the current build."
        )

    def _load_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in parsed if str(item).strip()] if isinstance(parsed, list) else []

    def _normalize_list(self, value, fallback: list[str]) -> list[str]:
        if isinstance(value, list):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return cleaned or fallback
        return fallback
