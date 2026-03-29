from pydantic import BaseModel


class CompanyRead(BaseModel):
    id: int
    name: str
    priority: int
    enabled: bool
    career_url: str | None = None

    class Config:
        from_attributes = True
