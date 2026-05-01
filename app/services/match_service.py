import json

from app.core.logging_config import get_logger
from app.models.models import Job, Profile
from app.services.ollama_client import OllamaClient

logger = get_logger(__name__)


class MatchService:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    def score(self, profile: Profile, job: Job, company_priority: int) -> tuple[float, str, str]:
        skills = set(self._load_list(profile.skills))
        target_roles = self._load_list(profile.target_roles)
        preferred_locations = self._load_list(profile.preferred_locations)

        text = f"{job.title} {job.description}".lower()
        overlap = len([skill for skill in skills if skill.lower() in text])
        skills_overlap = min(100.0, overlap * 20.0)
        role_match = 80.0 if any(role.lower() in job.title.lower() for role in target_roles) else 40.0
        location_match = 100.0 if not preferred_locations else 70.0
        seniority_match = 75.0
        keyword_similarity = 65.0

        score = (
            0.35 * skills_overlap
            + 0.20 * role_match
            + 0.15 * location_match
            + 0.10 * seniority_match
            + 0.10 * float(company_priority * 10)
            + 0.10 * keyword_similarity
        )

        explanation = self.ollama.chat_json(
            "Give concise JSON: {reason,missing_skills}."
            f"\nProfile summary: {profile.profile_summary}\nJob: {job.title}\nDescription: {job.description[:1800]}",
            fallback={"reason": "Strong keyword and role overlap.", "missing_skills": []},
        )

        logger.info(
            "match.score job_id=%s title=%s score=%.2f overlap=%s company_priority=%s",
            job.id,
            job.title,
            score,
            overlap,
            company_priority,
        )

        return score, explanation.get("reason", "Match computed."), json.dumps(explanation.get("missing_skills", []))

    def _load_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in parsed if str(item).strip()] if isinstance(parsed, list) else []
