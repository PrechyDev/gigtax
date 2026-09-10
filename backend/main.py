from fastapi import FastAPI
from core.config import settings
from api.routes import (
    advisory,
    assets,
    auth,
    custom_rules,
    dashboard,
    google_drive,
    receipts,
    reports,
    statements,
    tax_computations,
    transactions,
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for GigTax - AI-Powered Tax Preparation System",
    version="1.0.0"
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

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
