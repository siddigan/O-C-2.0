import re
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.logging_config import get_logger
from app.core.settings import settings
from app.models.models import Company

logger = get_logger(__name__)


@dataclass(frozen=True)
class DiscoveredJob:
    title: str
    location: str | None
    description: str
    apply_url: str
    source_confidence: float


class FirecrawlJobSearch:
    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.resolved_firecrawl_api_key()
        self.base_url = "https://api.firecrawl.dev/v2"
        self.quota_exhausted = False

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search_company_jobs(
        self,
        company: Company,
        limit: int | None = None,
        target_roles: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> list[DiscoveredJob]:
        if not self.api_key:
            logger.warning("firecrawl.search.skipped company=%s reason=missing_api_key", company.name)
            return []

        query = self._build_query(company, target_roles=target_roles, skills=skills)
        payload = {
            "query": query,
            "limit": limit or settings.firecrawl_search_limit,
            "sources": ["web"],
            "country": settings.firecrawl_country,
            "location": settings.firecrawl_location,
            "timeout": settings.firecrawl_timeout_ms,
            "ignoreInvalidURLs": True,
            "scrapeOptions": {"formats": [{"type": "markdown"}]},
        }

        include_domain = self._career_domain(company.career_url)
        if include_domain:
            payload["includeDomains"] = [include_domain]

        logger.info("firecrawl.search.start company=%s query=%s", company.name, query)

        try:
            with httpx.Client(timeout=(settings.firecrawl_timeout_ms / 1000) + 10) as client:
                response = client.post(
                    f"{self.base_url}/search",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 402:
                self.quota_exhausted = True
                logger.error("firecrawl.search.quota_exhausted company=%s", company.name)
                return []
            logger.exception("firecrawl.search.error company=%s", company.name)
            return []
        except httpx.HTTPError:
            logger.exception("firecrawl.search.error company=%s", company.name)
            return []

        body = response.json()
        if not body.get("success", False):
            logger.warning("firecrawl.search.failed company=%s response=%s", company.name, body)
            return []

        raw_results = (body.get("data") or {}).get("web") or []
        jobs = self._to_jobs(company, raw_results, target_roles=target_roles, skills=skills)
        logger.info(
            "firecrawl.search.complete company=%s results=%s jobs=%s credits=%s",
            company.name,
            len(raw_results),
            len(jobs),
            body.get("creditsUsed"),
        )
        return jobs

    def _build_query(
        self,
        company: Company,
        target_roles: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> str:
        roles = self._search_roles(target_roles)
        skill_terms = self._search_skills(skills)
        role_terms = " OR ".join(f'"{role}"' for role in roles)
        skills_clause = f' ({" OR ".join(skill_terms)})' if skill_terms else ""
        career_filter = ""
        domain = self._career_domain(company.career_url)
        if domain:
            career_filter = f" site:{domain}"
        locations_clause = " OR ".join(f'"{term}"' for term in self._location_terms())
        return f'{company.name} careers jobs ({role_terms}){skills_clause} ({locations_clause}){career_filter} -frontend -front-end -mobile -android -ios -indeed -linkedin'

    def _to_jobs(
        self,
        company: Company,
        raw_results: list[dict],
        target_roles: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> list[DiscoveredJob]:
        seen_urls: set[str] = set()
        jobs: list[DiscoveredJob] = []

        for result in raw_results:
            url = self._result_url(result)
            if not url or url in seen_urls or not self._looks_like_job_url(url):
                continue
            if not self._belongs_to_company_domain(company, url):
                logger.info("firecrawl.search.filtered_domain company=%s url=%s", company.name, url)
                continue

            title = self._clean_title(str(result.get("title") or ""), company.name)
            if not title or not self._looks_like_job_title(title):
                continue

            description = self._description(result)
            if not self._is_relevant_job(title, description, url, target_roles=target_roles, skills=skills):
                logger.info("firecrawl.search.filtered_irrelevant company=%s title=%s", company.name, title)
                continue

            jobs.append(
                DiscoveredJob(
                    title=title,
                    location=self._guess_location(title, description, url),
                    description=description,
                    apply_url=url,
                    source_confidence=0.85 if result.get("markdown") else 0.7,
                )
            )
            seen_urls.add(url)

        return jobs

    def _result_url(self, result: dict) -> str | None:
        metadata = result.get("metadata") or {}
        url = result.get("url") or metadata.get("sourceURL") or metadata.get("url")
        return self._canonical_url(str(url).strip()) if url else None

    def _description(self, result: dict) -> str:
        value = result.get("markdown") or result.get("description") or ""
        text = re.sub(r"\n{3,}", "\n\n", str(value)).strip()
        return text[:6000] or "Job discovered from Firecrawl search result."

    def _clean_title(self, title: str, company_name: str) -> str:
        cleaned = re.sub(r"\s+", " ", title).strip(" -|")
        cleaned = re.sub(rf"\s*[-|]\s*{re.escape(company_name)}.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*[-|]\s*Careers?.*$", "", cleaned, flags=re.IGNORECASE)
        return cleaned[:255]

    def _guess_location(self, title: str, description: str, url: str) -> str | None:
        first_lines = "\n".join(description.splitlines()[:30])
        haystack = f"{title}\n{url}\n{first_lines}"
        match = re.search(r"\b(Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Gurugram|Gurgaon|Noida|Remote|India)\b", haystack, re.IGNORECASE)
        return match.group(1) if match else None

    def _looks_like_job_url(self, url: str) -> bool:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        lowered = url.lower()
        path = parsed.path.lower().rstrip("/")
        if not path or path.endswith("/jobs") or "/search" in path or "/go/" in path:
            return False
        blocked_path_parts = (
            "/category/",
            "/blog",
            "/event-",
            "/talent-community/",
            "/location/",
            "/locations/",
            "/jobs/czech_republic",
        )
        if any(part in path for part in blocked_path_parts):
            return False

        job_markers = (
            "/job/",
            "/jobs/",
            "jobseqno=",
            "gh_jid=",
            "jobs.",
            "greenhouse.io",
            "lever.co",
            "workdayjobs",
            "myworkdayjobs",
            "ashbyhq",
            "/positions/",
            "/opening/",
            "/requisition/",
        )
        blocked = ("linkedin.com", "indeed.com", "glassdoor.com")
        return any(marker in lowered for marker in job_markers) and not any(domain in lowered for domain in blocked)

    def _looks_like_job_title(self, title: str) -> bool:
        lowered = title.lower()
        generic_titles = (
            "search result",
            "available job openings",
            "other jobs",
            "all jobs",
            "job search",
            "careers home",
            "search jobs",
            "search job opportunities",
            "apply today",
            "career site careers",
            "discover exciting job opportunities",
            "get to know",
        )
        if any(marker in lowered for marker in generic_titles):
            return False
        return not re.fullmatch(r"[\w\s&/+,-]+ jobs", lowered)

    def _is_relevant_job(
        self,
        title: str,
        description: str,
        url: str,
        target_roles: list[str] | None = None,
        skills: list[str] | None = None,
    ) -> bool:
        text = f"{title} {description} {url}".lower()
        title_lower = title.lower()
        roles = [role.lower() for role in self._search_roles(target_roles)]

        if self._wants_data_roles(roles):
            data_title_markers = (
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
            if "intern" in title_lower or "internship" in title_lower:
                return False
            return any(marker in title_lower for marker in data_title_markers) and self._is_india_job(title, description, url)

        return any(role in text for role in roles) if roles else True

    def _search_roles(self, target_roles: list[str] | None = None) -> list[str]:
        roles = [role.strip() for role in target_roles or [] if role.strip()]
        if any("data" in role.lower() for role in roles):
            return [
                "Data Engineer",
                "Analytics Engineer",
                "ETL Developer",
                "Data Platform Engineer",
                "Data Warehouse Engineer",
                "Big Data Engineer",
                "BI Engineer",
            ]
        return roles or ["Data Engineer", "Analytics Engineer", "ETL Developer"]

    def _search_skills(self, skills: list[str] | None = None) -> list[str]:
        preferred = []
        for skill in skills or []:
            normalized = skill.strip()
            if normalized.lower() in {"python", "sql", "aws", "snowflake", "postgresql", "docker", "airflow", "spark", "dbt"}:
                preferred.append(f'"{normalized}"' if " " in normalized else normalized)
        return preferred[:6]

    def _wants_data_roles(self, roles: list[str]) -> bool:
        return any("data" in role or "etl" in role or "analytics" in role or role.startswith("bi ") for role in roles)

    def _location_terms(self) -> list[str]:
        terms = [term.strip() for term in settings.firecrawl_location_terms.split(",") if term.strip()]
        return terms or ["India"]

    def _is_india_job(self, title: str, description: str, url: str) -> bool:
        text = f"{title} {description} {url}".lower()
        return any(
            re.search(rf"\b{re.escape(term.lower())}\b", text)
            for term in self._location_terms()
        )

    def _career_domain(self, career_url: str | None) -> str | None:
        if not career_url:
            return None
        parsed = urlparse(career_url if "://" in career_url else f"https://{career_url}")
        return parsed.netloc.lower().removeprefix("www.") or None

    def _belongs_to_company_domain(self, company: Company, url: str) -> bool:
        career_domain = self._career_domain(company.career_url)
        if not career_domain:
            return True

        candidate = urlparse(url).netloc.lower().removeprefix("www.")
        if candidate == career_domain or candidate.endswith(f".{career_domain}"):
            return True

        return self._root_domain(candidate) == self._root_domain(career_domain)

    def _root_domain(self, domain: str) -> str:
        parts = domain.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else domain

    def _canonical_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        query = parsed.query
        job_id_match = re.search(r"/job/([^/?]+)", path, re.IGNORECASE)
        if "americanexpress.com" in parsed.netloc.lower() and job_id_match:
            path = f"/job/{job_id_match.group(1)}"
            query = ""
        google_match = re.search(r"/jobs/results/([^/]+)", path, re.IGNORECASE)
        if "google.com" in parsed.netloc.lower() and google_match:
            path = f"/jobs/results/{google_match.group(1)}"
            query = ""

        keep_query = "apply" in path.lower() and any(key in query.lower() for key in ("jobseqno=", "jobid=", "gh_jid="))
        if not keep_query and re.search(r"/job/[^/]+", path, re.IGNORECASE):
            query = ""
        return urlunparse((parsed.scheme, parsed.netloc, path, "", query, ""))
