import json

from app.models.models import Job, Profile
from app.services.ollama_client import OllamaClient


class MatchService:
    def __init__(self) -> None:
        self.ollama = OllamaClient()

    def score(self, profile: Profile, job: Job, company_priority: int) -> tuple[float, str, str]:
        skills = set(json.loads(profile.skills or "[]"))
        text = f"{job.title} {job.description}".lower()
        overlap = len([s for s in skills if s.lower() in text])
        skills_overlap = min(100.0, overlap * 20.0)
        role_match = 80.0 if any(r.lower() in job.title.lower() for r in json.loads(profile.target_roles or "[]")) else 40.0
        location_match = 100.0 if not profile.preferred_locations else 70.0
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
        return score, explanation.get("reason", "Match computed."), json.dumps(explanation.get("missing_skills", []))
