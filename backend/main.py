from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logger import get_logger
from api.routes import (
    advisory,
    assets,
    auth,
    categories,
    custom_rules,
    dashboard,
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

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
