from pydantic import BaseModel, Field


class CompanyRead(BaseModel):
    id: int
    name: str
    priority: int
    enabled: bool
    career_url: str | None = None

    class Config:
        from_attributes = True


class CompanyCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    priority: int = Field(default=5, ge=1, le=10)
    enabled: bool = True
    career_url: str | None = None
