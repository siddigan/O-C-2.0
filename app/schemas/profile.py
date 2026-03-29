from pydantic import BaseModel


class ProfileCreate(BaseModel):
    target_roles: list[str] = []
    skills: list[str] = []
    preferred_locations: list[str] = []
    remote_preference: str = "hybrid"
    salary_min: int | None = None
    salary_max: int | None = None
    experience_years: float | None = None
    notice_period_days: int | None = None
    job_level: str | None = None


class ProfileRead(ProfileCreate):
    id: int
    profile_summary: str | None = None

    class Config:
        from_attributes = True
