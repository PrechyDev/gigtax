from fastapi import FastAPI
from core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for GigTax - AI-Powered Tax Preparation System",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": f"Welcome to the {settings.PROJECT_NAME} API"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
