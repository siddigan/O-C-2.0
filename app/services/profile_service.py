import json
import re
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
        fallback = self._parse_cv_locally(extracted_text, profile)
        parsed = self.ollama.chat_json(
            prompt,
            fallback=fallback,
        )

        profile.cv_path = cv_path
        profile.skills = json.dumps(self._normalize_list(parsed.get("skills"), self._load_list(profile.skills)))
        profile.target_roles = json.dumps(
            self._normalize_list(parsed.get("target_roles"), self._load_list(profile.target_roles))
        )
        profile.preferred_locations = json.dumps(
            self._normalize_list(parsed.get("preferred_locations"), self._load_list(profile.preferred_locations))
        )
        profile.profile_summary = parsed.get("profile_summary") or fallback["profile_summary"]

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

        if suffix == ".pdf":
            pdf_text = self._extract_pdf_text(path)
            if len(" ".join(pdf_text.split())) >= 80:
                return pdf_text

        decoded = raw_bytes.decode("utf-8", errors="ignore")
        compact = " ".join(decoded.split())

        if len(compact) >= 80:
            return compact

        logger.warning("profile.parse_cv.limited_extraction path=%s suffix=%s", str(path), suffix or "none")
        return (
            f"Uploaded resume file named {path.name}. "
            f"Automatic text extraction is limited for {suffix or 'this'} format in the current build."
        )

    def _extract_pdf_text(self, path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError:
            logger.warning("profile.parse_cv.pdf_dependency_missing install=pypdf")
            return ""

        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            logger.exception("profile.parse_cv.pdf_extract_error path=%s", str(path))
            return ""

    def _parse_cv_locally(self, text: str, profile: Profile) -> dict:
        existing_skills = self._load_list(profile.skills)
        existing_roles = self._load_list(profile.target_roles)
        existing_locations = self._load_list(profile.preferred_locations)

        known_skills = [
            "Python",
            "Java",
            "JavaScript",
            "TypeScript",
            "React",
            "Node.js",
            "FastAPI",
            "SQL",
            "PostgreSQL",
            "MySQL",
            "MongoDB",
            "AWS",
            "Azure",
            "Docker",
            "Kubernetes",
            "Git",
            "REST APIs",
            "Machine Learning",
            "Data Engineering",
            "Power BI",
            "Excel",
        ]
        lowered = text.lower()
        skills = [skill for skill in known_skills if skill.lower() in lowered]

        role_patterns = [
            "Software Engineer",
            "Backend Developer",
            "Frontend Developer",
            "Full Stack Developer",
            "Data Engineer",
            "Data Analyst",
            "Machine Learning Engineer",
        ]
        roles = [role for role in role_patterns if role.lower() in lowered]

        location_patterns = ["Bengaluru", "Bangalore", "Hyderabad", "Pune", "Chennai", "Mumbai", "Gurugram", "Noida", "Remote", "India"]
        locations = [location for location in location_patterns if re.search(rf"\b{re.escape(location)}\b", text, re.IGNORECASE)]

        summary = self._build_profile_summary(text, skills or existing_skills, roles or existing_roles)

        return {
            "skills": skills or existing_skills,
            "target_roles": roles or existing_roles,
            "preferred_locations": locations or existing_locations,
            "profile_summary": summary,
        }

    def _build_profile_summary(self, text: str, skills: list[str], roles: list[str]) -> str:
        compact = " ".join(text.split())
        years_match = re.search(r"(\d+(?:\.\d+)?)\+?\s+years?", compact, re.IGNORECASE)
        years = years_match.group(1) if years_match else None
        role = roles[0] if roles else "Data Engineer"
        skill_text = ", ".join(skills[:8]) if skills else "data pipelines, SQL, Python, and cloud data platforms"

        parts = [role]
        if years:
            parts.append(f"with {years}+ years of experience")
        else:
            parts.append("with experience")
        parts.append(f"in {skill_text}")

        if "snowflake" in compact.lower() or "aws" in compact.lower():
            parts.append("building cloud data pipelines and analytics datasets")

        return " ".join(parts) + "."

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
