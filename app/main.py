from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api import admin, auth, user, web
from app.core.settings import settings
from app.db.database import Base, SessionLocal, engine
from app.services.billing_job import run_monthly_billing

app = FastAPI(title=settings.app_name)
scheduler = BackgroundScheduler(timezone=settings.timezone)


@app.on_event("startup")
def startup() -> None:
    if settings.testing:
        return

    Base.metadata.create_all(bind=engine)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    def scheduled_billing() -> None:
        db = SessionLocal()
        try:
            run_monthly_billing(db)
        finally:
            db.close()

    if settings.enable_scheduler:
        scheduler.add_job(
            scheduled_billing,
            trigger="cron",
            day=1,
            hour=8,
            minute=0,
            id="monthly_billing",
            replace_existing=True,
        )
        if not scheduler.running:
            scheduler.start()


@app.on_event("shutdown")
def shutdown() -> None:
    if settings.testing:
        return

    if settings.enable_scheduler and scheduler.running:
        scheduler.shutdown(wait=False)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)
