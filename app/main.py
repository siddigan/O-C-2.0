from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from app.api.routes import router
from app.core.settings import settings
from app.db.session import Base, SessionLocal, engine
from app.services.search_service import SearchService

app = FastAPI(title=settings.app_name)
app.include_router(router)

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()


def scheduled_search() -> None:
    db = SessionLocal()
    try:
        SearchService(db).run_cycle(batch_size=5)
    finally:
        db.close()


if settings.scheduler_enabled:
    scheduler.add_job(scheduled_search, "interval", hours=12, id="search_cycle", replace_existing=True)
    scheduler.start()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "scheduler_enabled": settings.scheduler_enabled}
