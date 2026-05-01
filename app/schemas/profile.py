import json

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _coerce_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = [item.strip() for item in value.split(",") if item.strip()]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


class ProfileCreate(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    remote_preference: str = "hybrid"
    salary_min: int | None = None
    salary_max: int | None = None
    experience_years: float | None = None
    notice_period_days: int | None = None
    job_level: str | None = None

    @field_validator("target_roles", "skills", "preferred_locations", mode="before")
    @classmethod
    def parse_list_fields(cls, value):
        return _coerce_list(value)


class ProfileRead(ProfileCreate):
    id: int
    cv_path: str | None = None
    profile_summary: str | None = None

    model_config = ConfigDict(from_attributes=True)
