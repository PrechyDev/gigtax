# GigTax

AI-powered tax assessment and reporting system for Nigerian self-reporting taxpayers under the
Nigeria Tax Act 2025. See [`docs/SYSTEM_SPECIFICATION.md`](docs/SYSTEM_SPECIFICATION.md) for the full
feature specification and [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the build/deployment plan.

## Local setup

### Backend
```
cd backend
poetry install
cp .env.example .env   # fill in your own GEMINI_API_KEY
docker compose up -d db   # from the repo root, starts local Postgres
poetry run uvicorn main:app --reload
```

### Tests
```
cd backend
poetry run pytest
```
No test in this suite makes a real Gemini API call — all LLM calls are mocked. The manual pipeline
check (`backend/test_pipeline.py <file_path>`) does make real calls and is opt-in only, never run in CI.

### Frontend
Not yet scaffolded — see `docs/BUILD_PLAN.md` §4.
