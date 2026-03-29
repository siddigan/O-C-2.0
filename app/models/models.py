from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    target_roles: Mapped[str] = mapped_column(Text, default="[]")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    preferred_locations: Mapped[str] = mapped_column(Text, default="[]")
    remote_preference: Mapped[str] = mapped_column(String(32), default="hybrid")
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    notice_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cv_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    profile_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=5)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    career_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_json: Mapped[str] = mapped_column(Text, default="{}")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    apply_url: Mapped[str] = mapped_column(String(512), unique=True)
    posted_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    job_hash: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    source_confidence: Mapped[float] = mapped_column(Float, default=0.7)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("profiles.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), index=True)
    match_score: Mapped[float] = mapped_column(Float)
    fit_level: Mapped[str] = mapped_column(String(32))
    missing_skills: Mapped[str] = mapped_column(Text, default="[]")
    match_reason: Mapped[str] = mapped_column(Text)
    rank_score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
