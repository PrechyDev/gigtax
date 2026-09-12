import os
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logger import get_logger
from core.scheduled_cleanup import run_daily_cleanup
from api.routes import (
    advisory,
    assets,
    auth,
    categories,
    custom_rules,
    dashboard,
    filing_guidance,
    google_drive,
    receipts,
    reports,
    statements,
    tax_computations,
    transactions,
)

logger = get_logger("main")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for GigTax - AI-Powered Tax Preparation System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Last-resort safety net: nothing unhandled should ever leak a stack trace,
    provider error text, or internal detail to the client. The real exception is
    always logged server-side; the client only ever sees a generic, safe message.
    Specific failure modes (AI service down, Drive unreachable, etc.) are caught
    closer to their source with a more specific friendly message before they'd ever
    reach here — this handler is the catch-all for everything else.
    """
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Something went wrong on our end. Please try again shortly."},
    )


app.include_router(auth.router)
app.include_router(google_drive.router)
app.include_router(statements.router)
app.include_router(transactions.router)
app.include_router(custom_rules.router)
app.include_router(receipts.router)
app.include_router(tax_computations.router)
app.include_router(reports.router)
app.include_router(dashboard.router)
app.include_router(advisory.router)
app.include_router(assets.router)
app.include_router(categories.router)
app.include_router(filing_guidance.router)

# Daily housekeeping (purge discarded transactions / old chat sessions past their
# retention window — see core/scheduled_cleanup.py). A single in-process
# BackgroundScheduler is the right fit for a single Render free-tier dyno; no
# Redis/Celery needed for a once-a-day job. `next_run_time=` schedules an
# immediate first run too, so a long-running dev/demo instance doesn't wait a full
# day before its first cleanup.
scheduler = BackgroundScheduler(timezone="UTC")


@app.on_event("startup")
def _start_scheduler():
    # Guard against pytest: the test suite builds this same `app` inside a
    # `with TestClient(app) as client` block (see tests/conftest.py), which fires
    # startup events for real. Without this guard, every test using that fixture
    # would spin up a real scheduler thread whose immediate `next_run_time` job opens
    # a SessionLocal() against the real configured DATABASE_URI (not the test's
    # in-memory SQLite engine) — a stray real DB connection attempt on every test run.
    if os.environ.get("PYTEST_CURRENT_TEST") is not None:
        return
    scheduler.add_job(
        run_daily_cleanup,
        "interval",
        hours=24,
        next_run_time=datetime.now(timezone.utc),
        id="daily_cleanup",
        replace_existing=True,
    )
    scheduler.start()


@app.on_event("shutdown")
def _stop_scheduler():
    # Mirrors the pytest guard in _start_scheduler above — shutting down a scheduler
    # that was never started raises SchedulerNotRunningError, which every test using
    # the `client` fixture would otherwise hit on teardown.
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
