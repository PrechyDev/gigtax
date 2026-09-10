# GigTax

AI-powered tax assessment and reporting system for Nigerian self-reporting taxpayers under the
Nigeria Tax Act 2025. See [`docs/SYSTEM_SPECIFICATION.md`](docs/SYSTEM_SPECIFICATION.md) for the full
feature specification and [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the build/deployment plan.

## Local setup

### Backend
```
docker compose up -d db          # from the repo root, starts local Postgres
cd backend
poetry install
cp .env.example .env             # fill in your own GEMINI_API_KEY (see below for the rest)
poetry run alembic upgrade head  # creates all tables
poetry run python -m scripts.seed_categories   # loads the NTA-2025-aligned category taxonomy
poetry run uvicorn main:app --reload
```

Auth (`JWT_SECRET_KEY`) and Google Drive BYOS (`FERNET_SECRET_KEY`, `GOOGLE_CLIENT_ID`/
`GOOGLE_CLIENT_SECRET`) each need real values in `.env` — see the generation commands and
setup notes inside `.env.example`. Without a real `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`
(register one in Google Cloud Console, scope `drive.file`), the `/auth/google/*` endpoints
will fail — everything else works without them.

API docs (Swagger UI) once running: http://localhost:8000/docs

### Tests
```
cd backend
poetry run pytest
```
No test in this suite makes a real Gemini API call — all LLM calls are mocked. The manual pipeline
check (`backend/test_pipeline.py <file_path>`) does make real calls and is opt-in only, never run in CI.

### Frontend
Not yet scaffolded — see `docs/BUILD_PLAN.md` §4.
