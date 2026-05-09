from email.message import EmailMessage
import json
import smtplib

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.settings import settings
from app.models.models import Company, Job, JobMatch, Profile
from app.services.match_service import MatchService

logger = get_logger(__name__)


class JobReportEmailService:
    def __init__(self, db: Session):
        self.db = db

    def send_sample_email(self) -> dict:
        if not self._is_configured():
            reason = self._missing_config_reason()
            logger.warning("job_report.sample_email.skipped reason=%s", reason)
            return {"sent": False, "reason": reason}

        message = EmailMessage()
        smtp_username = settings.smtp_username or settings.job_report_to_email
        message["Subject"] = "OC2 email test"
        message["From"] = settings.smtp_from_email or smtp_username
        message["To"] = settings.job_report_to_email
        message.set_content("OC2 email test succeeded. Sender and recipient are configured.")
        return self._send_message(message, sample=True)

    def send_top_jobs_report(self, limit: int = 15) -> dict:
        if not self._is_configured():
            reason = self._missing_config_reason()
            logger.warning("job_report.email.skipped reason=%s", reason)
            return {"sent": False, "reason": reason}

        jobs = self._top_jobs(limit)
        if not jobs:
            logger.info("job_report.email.skipped reason=no_jobs")
            return {"sent": False, "reason": "no_jobs"}

        message = EmailMessage()
        message["Subject"] = f"OC2 top {len(jobs)} jobs"
        smtp_username = settings.smtp_username or settings.job_report_to_email
        message["From"] = settings.smtp_from_email or smtp_username
        message["To"] = settings.job_report_to_email
        message.set_content(self._plain_text(jobs))
        message.add_alternative(self._html(jobs), subtype="html")
        result = self._send_message(message, sample=False)
        if result.get("sent"):
            result["jobs"] = len(jobs)
        return result

    def _send_message(self, message: EmailMessage, sample: bool) -> dict:
        smtp_username = settings.smtp_username or settings.job_report_to_email
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_password:
                    smtp.login(smtp_username, settings.smtp_password.get_secret_value())
                smtp.send_message(message)
        except Exception:
            logger.exception("job_report.email.error to=%s", settings.job_report_to_email)
            return {"sent": False, "reason": "smtp_error"}

        logger.info("job_report.email.sent to=%s sample=%s", settings.job_report_to_email, sample)
        return {"sent": True, "sample": sample, "to": settings.job_report_to_email}

    def _top_jobs(self, limit: int) -> list[dict]:
        profile = self.db.query(Profile).first()
        rows = self.db.query(Job, Company).join(Company, Company.id == Job.company_id).all()
        if not rows:
            return []

        if not profile:
            return [
                {
                    "title": job.title,
                    "company": company.name,
                    "score": None,
                    "fit_level": "unranked",
                    "location": job.location,
                    "apply_url": job.apply_url,
                    "reason": "No profile exists yet, so jobs are sorted by newest first.",
                }
                for job, company in sorted(rows, key=lambda row: row[0].created_at, reverse=True)[:limit]
            ]

        latest_matches = self._latest_matches_by_job()
        missing_job_ids = [job.id for job, _company in rows if job.id not in latest_matches]
        if missing_job_ids:
            self._score_missing_matches(profile, rows, set(missing_job_ids))
            latest_matches = self._latest_matches_by_job()

        output = []
        for job, company in rows:
            match = latest_matches.get(job.id)
            output.append(
                {
                    "title": job.title,
                    "company": company.name,
                    "score": match.match_score if match else 0,
                    "fit_level": match.fit_level if match else "unranked",
                    "location": job.location,
                    "apply_url": job.apply_url,
                    "reason": match.match_reason if match else "No match was generated.",
                }
            )

        return sorted(output, key=lambda item: float(item["score"] or 0), reverse=True)[:limit]

    def _latest_matches_by_job(self) -> dict[int, JobMatch]:
        matches = self.db.query(JobMatch).order_by(JobMatch.created_at.desc()).all()
        latest: dict[int, JobMatch] = {}
        for match in matches:
            latest.setdefault(match.job_id, match)
        return latest

    def _score_missing_matches(self, profile: Profile, rows: list[tuple[Job, Company]], missing_job_ids: set[int]) -> None:
        matcher = MatchService()
        for job, company in rows:
            if job.id not in missing_job_ids:
                continue
            score, reason, missing = matcher.score(profile, job, company.priority)
            fit_level = "high" if score >= 75 else "medium" if score >= 55 else "low"
            self.db.add(
                JobMatch(
                    profile_id=profile.id,
                    job_id=job.id,
                    match_score=score,
                    fit_level=fit_level,
                    missing_skills=missing or json.dumps([]),
                    match_reason=reason,
                    rank_score=score,
                )
            )
        self.db.commit()

    def _plain_text(self, jobs: list[dict]) -> str:
        lines = ["Top OC2 job matches", ""]
        for index, job in enumerate(jobs, start=1):
            score = "unranked" if job["score"] is None else f'{float(job["score"]):.1f}'
            lines.extend(
                [
                    f'{index}. {job["title"]} - {job["company"]} ({score})',
                    f'Location: {job["location"] or "Not specified"}',
                    f'Fit: {job["fit_level"]}',
                    f'Apply: {job["apply_url"]}',
                    f'Reason: {job["reason"]}',
                    "",
                ]
            )
        return "\n".join(lines)

    def _html(self, jobs: list[dict]) -> str:
        items = []
        for index, job in enumerate(jobs, start=1):
            score = "unranked" if job["score"] is None else f'{float(job["score"]):.1f}'
            items.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td><strong>{self._escape(job['title'])}</strong><br>{self._escape(job['company'])}</td>"
                f"<td>{self._escape(score)}</td>"
                f"<td>{self._escape(job['location'] or 'Not specified')}</td>"
                f"<td><a href=\"{self._escape(job['apply_url'])}\">Apply</a></td>"
                "</tr>"
            )
        return (
            "<html><body><h2>Top OC2 job matches</h2>"
            "<table border=\"1\" cellpadding=\"8\" cellspacing=\"0\">"
            "<thead><tr><th>#</th><th>Job</th><th>Score</th><th>Location</th><th>Link</th></tr></thead>"
            f"<tbody>{''.join(items)}</tbody></table></body></html>"
        )

    def _escape(self, value: object) -> str:
        return (
            str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    def _is_configured(self) -> bool:
        return self._missing_config_reason() is None

    def _missing_config_reason(self) -> str | None:
        if not settings.job_report_to_email:
            return "missing_job_report_to_email"
        if not settings.smtp_host:
            return "missing_smtp_host"
        if not settings.smtp_password:
            return "missing_smtp_password"
        return None
