import hashlib
import json
import re

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.settings import settings
from app.models.models import Company, Job, Profile
from app.services.email_service import JobReportEmailService
from app.services.firecrawl_service import DiscoveredJob, FirecrawlJobSearch

logger = get_logger(__name__)


class SearchService:
    def __init__(self, db: Session):
        self.db = db
        self.firecrawl = FirecrawlJobSearch()

    def run_cycle(self, batch_size: int | None = None, send_report: bool | None = None) -> dict:
        resolved_batch_size = batch_size or settings.search_batch_size
        companies = (
            self.db.query(Company)
            .filter(Company.enabled.is_(True), Company.career_url.is_not(None))
            .order_by(Company.priority.desc())
            .limit(resolved_batch_size)
            .all()
        )

        logger.info("search.run_cycle.start batch_size=%s companies=%s", resolved_batch_size, len(companies))

        samples_removed = self._delete_sample_jobs() if not settings.search_allow_sample_fallback else 0
        target_roles, skills = self._profile_search_terms()
        irrelevant_removed = self._delete_irrelevant_jobs(target_roles, skills)
        discovered = 0
        companies_with_results = 0
        quota_exhausted = False
        for company in companies:
            jobs = self.firecrawl.search_company_jobs(company, target_roles=target_roles, skills=skills)
            if self.firecrawl.quota_exhausted:
                quota_exhausted = True
                logger.warning("search.run_cycle.stopped reason=firecrawl_quota_exhausted company=%s", company.name)
                break
            if not jobs and settings.search_allow_sample_fallback:
                jobs = [self._sample_job(company)]

            if jobs:
                companies_with_results += 1

            for discovered_job in jobs:
                if self._insert_job(company, discovered_job):
                    discovered += 1
            self.db.commit()

        self.db.commit()
        email_result = None
        should_send_report = settings.job_report_after_search if send_report is None else send_report
        if should_send_report:
            email_result = JobReportEmailService(self.db).send_top_jobs_report(limit=15)

        result = {
            "companies_processed": len(companies),
            "companies_with_results": companies_with_results,
            "jobs_inserted": discovered,
            "sample_jobs_removed": samples_removed,
            "irrelevant_jobs_removed": irrelevant_removed,
            "firecrawl_configured": self.firecrawl.is_configured,
            "firecrawl_quota_exhausted": quota_exhausted,
            "email_report": email_result,
        }
        logger.info(
            "search.run_cycle.complete companies=%s companies_with_results=%s jobs_inserted=%s",
            len(companies),
            companies_with_results,
            discovered,
        )
        return result

    def _insert_job(self, company: Company, discovered_job: DiscoveredJob) -> bool:
        job_hash = hashlib.sha1(
            f"{company.name}|{discovered_job.title}|{discovered_job.apply_url}".encode("utf-8")
        ).hexdigest()
        canonical_path = discovered_job.apply_url.split("?", 1)[0]
        exists = (
            self.db.query(Job)
            .filter(
                (Job.job_hash == job_hash)
                | (Job.apply_url == discovered_job.apply_url)
                | (Job.apply_url.like(f"{canonical_path}?%"))
            )
            .first()
        )
        if exists:
            logger.info("search.job.skipped company=%s reason=existing_job url=%s", company.name, discovered_job.apply_url)
            return False

        self.db.add(
            Job(
                company_id=company.id,
                title=discovered_job.title,
                location=discovered_job.location,
                description=discovered_job.description,
                apply_url=discovered_job.apply_url,
                job_hash=job_hash,
                source_confidence=discovered_job.source_confidence,
            )
        )
        logger.info("search.job.created company=%s title=%s apply_url=%s", company.name, discovered_job.title, discovered_job.apply_url)
        return True

    def _sample_job(self, company: Company) -> DiscoveredJob:
        title = f"Sample {company.name} Role"
        apply_url = f"{company.career_url.rstrip('/')}/sample-role"
        return DiscoveredJob(
            title=title,
            location="Remote",
            description="Placeholder job used only when SEARCH_ALLOW_SAMPLE_FALLBACK=true.",
            apply_url=apply_url,
            source_confidence=0.35,
        )

    def _delete_sample_jobs(self) -> int:
        deleted = (
            self.db.query(Job)
            .filter(Job.title.like("Sample % Role"), Job.source_confidence <= 0.35)
            .delete(synchronize_session=False)
        )
        if deleted:
            logger.info("search.sample_jobs.removed count=%s", deleted)
        return deleted

    def _profile_search_terms(self) -> tuple[list[str], list[str]]:
        profile = self.db.query(Profile).first()
        if not profile:
            return ["Data Engineer"], []
        return self._load_list(profile.target_roles) or ["Data Engineer"], self._load_list(profile.skills)

    def _load_list(self, value: str | None) -> list[str]:
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return [str(item).strip() for item in parsed if str(item).strip()] if isinstance(parsed, list) else []

    def _delete_irrelevant_jobs(self, target_roles: list[str], skills: list[str]) -> int:
        if not any("data" in role.lower() for role in target_roles):
            return 0

        jobs = self.db.query(Job).all()
        irrelevant_ids = [
            job.id
            for job in jobs
            if not self._job_matches_data_profile(job, skills)
        ]
        if not irrelevant_ids:
            return 0

        deleted = self.db.query(Job).filter(Job.id.in_(irrelevant_ids)).delete(synchronize_session=False)
        logger.info("search.irrelevant_jobs.removed count=%s", deleted)
        return deleted

    def _job_matches_data_profile(self, job: Job, skills: list[str]) -> bool:
        title = job.title.lower()
        url = job.apply_url.lower()
        text = f"{job.title} {job.description}".lower()
        blocked_title_parts = ("discover exciting job opportunities", "get to know", "search engineering jobs")
        blocked_url_parts = ("/category/", "/blog", "/event-", "/talent-community/", "/location/", "/locations/")
        if "intern" in title or "internship" in title:
            return False
        if any(part in title for part in blocked_title_parts) or any(part in url for part in blocked_url_parts):
            return False
        title_markers = (
            "data engineer",
            "data engineering",
            "analytics engineer",
            "etl",
            "elt",
            "data platform",
            "data warehouse",
            "big data",
            "business intelligence",
            "bi engineer",
            "snowflake",
        )
        broad_markers = title_markers + ("pipeline", "pipelines", "sql", "python", "aws", "spark", "airflow", "dbt", "databricks")
        return any(marker in title for marker in title_markers) and self._job_has_india_location(job)

    def canonical_job_key(self, job: Job) -> tuple[int, str]:
        url = job.apply_url.split("?", 1)[0].lower()
        match = re.search(r"americanexpress\.com/.*/job/([^/?]+)", url)
        if match:
            url = f"americanexpress.com/job/{match.group(1)}"
        google_match = re.search(r"google\.com/(?:.*/)?jobs/results/([^/]+)", url)
        if google_match:
            url = f"google.com/jobs/results/{google_match.group(1)}"
        return job.company_id, url

    def _job_has_india_location(self, job: Job) -> bool:
        terms = [term.strip().lower() for term in settings.firecrawl_location_terms.split(",") if term.strip()]
        text = f"{job.title} {job.location or ''} {job.description} {job.apply_url}".lower()
        return any(re.search(rf"\b{re.escape(term)}\b", text) for term in terms)
