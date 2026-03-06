from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, user, web
from app.core.settings import settings
from app.db.database import Base, SessionLocal, engine
from app.services.billing_job import run_monthly_billing

app = FastAPI(title=settings.app_name)
scheduler = BackgroundScheduler(timezone=settings.timezone)


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)

    def scheduled_billing() -> None:
        db = SessionLocal()
        try:
            run_monthly_billing(db)
        finally:
            db.close()

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
    if scheduler.running:
        scheduler.shutdown(wait=False)


app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(web.router)
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)
