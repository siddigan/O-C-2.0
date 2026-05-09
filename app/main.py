from time import perf_counter
from uuid import uuid4

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.logging_config import get_logger, setup_logging
from app.core.settings import settings
from app.db.session import Base, SessionLocal, engine
from app.services.email_service import JobReportEmailService
from app.services.search_service import SearchService

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name)
app.include_router(router)

Base.metadata.create_all(bind=engine)

app.mount("/ui", StaticFiles(directory="frontend", html=True), name="ui")


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    path = request.url.path
    should_log = not path.startswith("/ui") and path not in {"/admin/logs", "/favicon.ico"}
    request_id = uuid4().hex[:8]
    started_at = perf_counter()

    if should_log:
        logger.info("request.start id=%s method=%s path=%s", request_id, request.method, path)

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.exception("request.error id=%s method=%s path=%s duration_ms=%s", request_id, request.method, path, duration_ms)
        raise

    response.headers["X-Request-ID"] = request_id
    if should_log:
        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        logger.info(
            "request.complete id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            path,
            response.status_code,
            duration_ms,
        )
    return response


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


scheduler = BackgroundScheduler()


def scheduled_search() -> None:
    db = SessionLocal()
    try:
        logger.info("scheduler.search.start")
        SearchService(db).run_cycle(batch_size=5)
        logger.info("scheduler.search.complete")
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    logger.info("app.start title=%s scheduler_enabled=%s", settings.app_name, settings.scheduler_enabled)


@app.on_event("shutdown")
def on_shutdown() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

    if not settings.job_report_on_shutdown:
        logger.info("app.shutdown job_report=disabled")
        return

    db = SessionLocal()
    try:
        logger.info("app.shutdown job_report.start")
        JobReportEmailService(db).send_top_jobs_report(limit=15)
    finally:
        db.close()


if settings.scheduler_enabled:
    scheduler.add_job(scheduled_search, "interval", hours=12, id="search_cycle", replace_existing=True)
    scheduler.start()
    logger.info("scheduler.started interval_hours=12")
else:
    logger.info("scheduler.disabled")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "scheduler_enabled": settings.scheduler_enabled}
