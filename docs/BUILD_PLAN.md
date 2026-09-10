# GigTax — Build Plan (MVP)

Companion to `SYSTEM_SPECIFICATION.md`. That document says *what* the system is; this one says *in
what order, by whom (role), and how* we build it — sequenced to get a working MVP fast, on a
zero/low-budget stack, without overengineering.

## 1. Repo Strategy

**Recommendation: one repository, not two.**

- You're a solo student developer. Two repos (frontend/backend) buy you nothing at this scale — they
  cost you: cross-repo PRs every time an API contract changes, two CI configs, two issue trackers, and
  constant "which repo was that in" friction.
- A single repo also matches what's already here: `Implementation/` already holds `backend/`, `docs/`,
  `scripts/`, `.agents/` as siblings — `frontend/` just becomes another sibling.
- Concrete structure:
  ```
  Implementation/                 <- becomes the git repo root
  ├── backend/
  ├── frontend/                   <- new
  ├── docs/
  ├── scripts/
  ├── .agents/
  ├── docker-compose.yml
  ├── .gitignore
  └── README.md                   <- new, top-level project readme
  ```
- **Do not** put this repo's root at the parent `Final year project/` folder — that folder also holds
  the academic report (`.docx`/`.pdf`) and slides, which are a different artifact with a different
  lifecycle and shouldn't be versioned alongside code (and the report docx files are multi-MB binaries
  that don't belong in a code repo's history).
- Free-tier hosting (Vercel, Render, Railway, Fly.io) all support **monorepos with a subdirectory root**
  (e.g. Vercel's "Root Directory" setting, Render's "Root Directory" per service) — this is a solved
  problem on every platform you'd actually use here, so there's no deployment reason to split either.
- **When it would make sense to split**: if this ever grows a second consumer of the API (e.g. a
  mobile app) or a second team with different release cadences. Not an MVP concern — revisit later if
  it happens.

**Action item**: `git init` inside `Implementation/`, add a `.gitignore` covering `.env`,
`__pycache__/`, `node_modules/`, `dist/`, `*.pyc`, `.venv/`, and the sample bank-statement files
currently sitting in `scripts/` (`Customer Statement.pdf`, `Customer Statement.xlsx`,
`My Bank Statement.pdf`, `statement.pdf`) — these may be real personal financial data and should not
enter git history even once. Move them to a `scripts/fixtures/` folder that's gitignored, or replace
with synthetic sample data.

## 2. Guiding Principles (apply to every task below)

- **Modularity**: parsing / sanitization / categorization / computation / advisory / reporting stay
  independent modules with narrow interfaces, same pattern as `backend/modules/ai_categorization/`
  already in place. A router calls a service; a service doesn't reach into another service's guts.
- **TDD**: for new business logic (computation engine, ingestion routing, review workflow), write the
  test first (or immediately alongside), following the existing `pytest` + `unittest.mock` style. LLM
  calls are always mocked in the default test suite — never make real Gemini calls from `pytest`.
- **No overengineering**: build exactly what §3/§7 of the spec asks for. No plugin systems, no generic
  "tax type" abstraction for CIT/VAT that doesn't exist yet, no premature multi-tenancy.
- **Cost discipline**: local-first for parsing, Gemini only when necessary, `pgvector` instead of a
  second vector-DB service, free hosting tiers, mocked tests.

## 3. Backend Build Plan

Sequenced so each step produces something runnable/testable, not a half-finished layer.

### Phase B0 — Foundations (unblocks everything else)
1. `git init`, `.gitignore`, top-level `README.md` (setup instructions: `poetry install`,
   `docker compose up db`, env vars needed).
2. Wire up **Alembic**: `alembic init`, point `env.py` at `db.base.Base.metadata` and
   `settings.SQLALCHEMY_DATABASE_URI`, generate the initial migration from the existing 9 models,
   apply it. (This has been a declared-but-unused dependency — first real gap to close.)
3. Seed script: load `db/seed_data/categories.json` into the `categories` table on startup/first
   migration (idempotent — upsert by `developer_slug`).
4. Add `alembic upgrade head` (or equivalent) to a documented local setup step and to whatever CI/
   deploy step runs migrations.

### Phase B1 — Auth (blocks every user-scoped endpoint)
5. `User` registration/login endpoints: password hashing (`passlib[bcrypt]`), JWT issue/verify
   (`python-jose` or `pyjwt`), a `get_current_user` FastAPI dependency.
6. Tests: registration, login (correct/incorrect password), protected-route rejection without a
   token — all against a test DB or mocked session, no real network calls involved so this is cheap
   to test thoroughly.

### Phase B1.5 — Google Drive Connection (BYOS)
Do this right after auth, since receipts depend on it and it's the project's core privacy/security
differentiator — not deferred to post-MVP.
7. GCP setup (one-time, outside the codebase): reuse the existing GCP project (the one issuing the
   Gemini API key) to register an OAuth 2.0 Web Client, configure the consent screen for the
   **`https://www.googleapis.com/auth/drive.file`** scope only, add the local + deployed redirect URIs.
8. `GET /auth/google/connect`: builds the Google consent URL (`access_type=offline`,
   `prompt=consent` to force a refresh token on reconnect) for the current authenticated user,
   redirects.
9. `GET /auth/google/callback`: exchanges the auth code for tokens, encrypts the refresh token
   (`cryptography.fernet`, key from an env var — add `FERNET_SECRET_KEY` to `.env`/`Settings`),
   creates the "GigTax Documents" folder via the Drive API on first connection, stores
   `google_refresh_token_encrypted` + `google_drive_folder_id`, sets `google_drive_connected = true`.
10. `DriveService` wrapper (`backend/services/drive_service.py`, same singleton-facade pattern as
    `llm_service.py`): decrypt the stored refresh token, refresh an access token, `upload(file_bytes,
    filename) -> file_id`, `get_download_link(file_id)`. All Drive calls go through this one module —
    nothing else touches the Drive API directly.
11. Tests: mock the Google API client entirely (`unittest.mock.patch`, same style as the LLM tests) —
    no real OAuth flow or real Drive calls in the test suite. A short manual/opt-in script (mirroring
    `test_pipeline.py`) is fine for one-time real verification that the flow works end to end.
12. Wire `Receipt` upload endpoints (built alongside ingestion in B2 below) to require
    `google_drive_connected`; if not connected, respond with a clear "connect Google Drive first" error
    the frontend can turn into a prompt — this only gates receipts, not statement parsing or manual
    entry, both of which never needed persistent storage in the first place.

### Phase B2 — Ingestion API (multi-file + images + manual entry)
13. Extend `modules/ai_categorization/parsing.py`:
    - Add an image branch to `extract_text` (`.jpg`/`.jpeg`/`.png`) that calls `parse_with_gemini` with
      the correct `mime_type` (currently defaults to `application/pdf` — needs to accept/pass the real
      one) and a **different prompt** tuned for handwritten/freeform notes rather than tabular bank
      statements (the current prompt assumes columnar data).
    - Unit tests for the new branch, mocking `llm_service.generate_vision_text` exactly like the
      existing parsing tests mock other pieces.
14. `POST /statements` accepting `List[UploadFile]` (multipart): create one `StatementUpload` per file,
    process each independently (one failure doesn't fail the batch), return per-file status.
    - On `PasswordRequiredError` for a given file → that file's response entry is `423`-equivalent
      (documented in `.agents/AGENTS.md`); batch continues for the rest.
15. `POST /transactions` (manual entry): create an `IncomeRecord`/`ExpenseRecord` directly from
    user-submitted fields, no parsing pipeline involved.
16. Tests for both endpoints using FastAPI's `TestClient`, with the categorization/parsing pipeline
    mocked at the boundary (don't re-test parsing logic here, just that the endpoint wires it up and
    persists correctly).

### Phase B3 — Review workflow
17. `GET /transactions?review_status=PENDING` (+ filters for tax year, source), `PATCH /transactions/{id}`
    (approve/correct category/reject), `POST /custom-rules`.
18. Enforce the "only APPROVED transactions reach computation" invariant at the computation engine's
    input boundary (query filter), not scattered across callers.

### Phase B4 — Tax computation engine (the core deliverable) — DONE
19. `backend/modules/tax_computation/engine.py` — pure module implementing spec §6's stages, taking a
    list of approved transactions + a tax year, returning a result object (`total_income`,
    `total_deductions`, `total_reliefs`, `total_capital_allowances`, `chargeable_income`, per-band
    breakdown, `net_tax`).
20. **Tests written first**: hand-computed scenarios across income levels (below ₦800k → zero tax; a
    mid-band case spanning bands; rent relief capped at ₦500k; the minimum-wage exemption case; a
    capital asset case) — no database, no LLM, fast and free to run constantly.
21. `total_reliefs` and `total_capital_allowances` columns added to `TaxComputation` (the schema
    originally conflated deductions/reliefs, and had no capital-allowance concept at all).
22. `POST /tax-computations/{tax_year}/compute` / `GET /tax-computations/{tax_year}` endpoints.
23. **Capital Asset Handling (First Schedule capital allowances) — mandatory, added mid-build.**
    `backend/modules/tax_computation/capital_allowances.py` (pure: class → rate/useful-life table,
    per-year allowance calc) + a real `Asset` model + `backend/modules/ingestion/asset_sync.py`, which
    every write path that can set a transaction's category (AI ingestion, manual entry, review
    corrections) calls to keep exactly one `Asset` row in sync with whether that transaction is
    currently categorized as one. `GET /assets` (shows each asset's computed current-year allowance)
    and `PATCH /assets/{id}/dispose`.

### Phase B5 — Reporting
23. Report generation: assemble computation + transactions into a downloadable document (a simple
    server-rendered PDF, e.g. `weasyprint` or `reportlab` — pick whichever has the least setup friction;
    don't reach for a paid PDF-generation API). `TaxReport` row + `GET /tax-computations/{tax_year}/report`.

### Phase B6 — AI Advisor (RAG) — DONE
24. `backend/modules/advisory/document_ingestion.py`: extracts a PDF page-by-page (`pdfplumber` →
    `pymupdf` fallback, reusing the same tiered approach as statement parsing), chunks each page
    (fixed-size with overlap, kept within a page so citations stay exact), embeds each chunk
    (`gemini-embedding-001` — verified directly against the API; `text-embedding-004`, assumed at
    first, turned out to be retired), stores into a new `knowledge_chunks` table (`pgvector`).
    `backend/scripts/ingest_document.py` is the reusable CLI entry point — re-run it any time to add
    or update a document; it replaces that `source_title`'s chunks rather than duplicating them.
    **Local Docker must use the `pgvector/pgvector:pg15` image, not stock `postgres:15`** — the
    extension isn't present otherwise (`docker-compose.yml` updated); Neon has it built in already.
25. `backend/modules/advisory/retrieval.py`: embeds the question, cosine-similarity top-k against
    `knowledge_chunks` (no ANN index needed at this corpus size). `backend/modules/advisory/
    rag_advisor.py` builds the grounded prompt (system prompt explicitly forbids answering outside
    the retrieved passages) and calls `llm_service.generate_text`.
26. `POST /advisory/query` logs real citations (e.g. `"Nigeria Tax Act 2025 (p.30)"`) to
    `AIAdvisoryQuery.retrieved_sources` as JSON, replacing the previous build's `"static_context_v1"`
    placeholder marker.
27. Tests mock `retrieve_relevant_chunks`/`generate_embedding`/`generate_text` at the module boundary
    — `knowledge_chunks` uses a `pgvector` column type that doesn't compile under the SQLite test
    engine, so it's excluded from the SQLite test schema entirely (see `tests/conftest.py`) rather
    than exercised directly in the automated suite.
28. Ingested the full Nigeria Tax Act 2025 gazette PDF as the primary (and, for now, only) knowledge
    source — a real, necessary bulk call (~200+ embedding requests), not a wasted one. Added
    exponential-backoff retry to `generate_embedding` specifically because a bulk ingestion job is
    much more likely to hit free-tier rate limits than a single interactive call.

## 4. Frontend Build Plan

React + Vite + TypeScript + Tailwind + TanStack Query. No heavier state library needed for an MVP —
server state lives in React Query caches, local UI state in component state/context.

### Phase F0 — Scaffolding
1. `npm create vite@latest frontend -- --template react-ts`, Tailwind setup, a thin typed API client
   (fetch wrapper + generated or hand-written types matching the backend's Pydantic response models —
   keep these in sync manually for MVP; codegen is a nice-to-have, not a requirement).
2. Auth pages (login/register), token storage (memory + refresh via httpOnly cookie if time allows,
   otherwise localStorage for MVP simplicity — acceptable trade-off, not a bank), route guarding.
3. "Connect Google Drive" step in onboarding: button → redirect to `/auth/google/connect` → backend
   handles the round trip → app redirects back with connected/not-connected state reflected in the
   user's profile. Show connection status somewhere persistent (settings page, dashboard badge) since
   it gates receipt uploads later.

### Phase F1 — Ingestion UI
4. Upload screen: drag-and-drop / file picker accepting **multiple files**, mixed types
   (`.pdf,.csv,.xlsx,.xls,.jpg,.jpeg,.png`), per-file progress/status list (matches one
   `StatementUpload` row per file).
5. Password modal: triggered on a `423` response for a specific file, resubmits just that file with
   the password, never persists the password client-side beyond the request.
6. Manual entry form: date/description/amount/direction/category fields, client-side validation.

### Phase F2 — Review UI
7. Review queue: list of pending transactions, AI-suggested category + confidence shown, inline
   approve/correct/reject actions, "create a rule from this" shortcut.

### Phase F3 — Computation & Dashboard
8. Dashboard: gross income, approved deductions, pending review count, estimated liability, filing
   deadline reminder (static per tax year, not dynamically fetched from anywhere external for MVP).
9. Tax computation page: full stage-by-stage breakdown (income → deductions → reliefs → chargeable
   income → per-band tax → total), matching spec §6 exactly so the numbers are auditable by the user.

### Phase F4 — Reporting & Advisor
10. Report page: preview + download link for the generated report.
11. Advisor chat: simple message list + input, calls `/advisory/query`, shows cited sources.

## 5. Testing Strategy

- **Backend**: `pytest`, mocks for every LLM/vision call (pattern already established in
  `test_categorization.py`), a test database (SQLite in-memory or a disposable Postgres via
  `docker compose` for CI — SQLite is fine for MVP since nothing here relies on Postgres-only features
  except `pgvector`, which the advisory-module tests should mock around entirely rather than exercise).
- **Tax computation engine** gets the most thorough test coverage of anything in the system (see B4/20)
  since it's the one place correctness is the whole point.
- **Frontend**: component/unit tests optional for MVP speed, but at minimum manually verify the golden
  path (upload → review → compute → report) and the image-ingestion path in a real browser before
  calling a phase done — type checking isn't a substitute for actually seeing it work.
- **No automated test may hit the real Gemini API.** The only real-API touchpoints are:
  `backend/test_pipeline.py` (manual CLI), and, if useful, a manual advisory-quality check script — both
  explicitly excluded from `pytest`/CI runs.
- **CI** (once a repo exists): a simple GitHub Actions workflow running `poetry install && poetry run
  pytest` on push — free on GitHub for a public/student repo, no reason to skip it.

## 6. Deployment Plan (free-tier, concrete choices)

These are firm decisions, not options to pick between later — every one is chosen so the project never
needs a paid tier to run.

### Environments — two, not three
- **Local dev**: the existing `docker-compose.yml` Postgres container (`postgres:15`). This is where
  you develop and where `pytest` runs against (or SQLite in-memory for pure unit tests — see §5). It is
  **never** the database the deployed app talks to.
- **Deployed (demo/production, one environment, not split into staging+prod)**: a single **Neon**
  project. A student MVP with one developer doesn't need a separate staging tier — if you want a safe
  place to test a migration before it hits the real data, use a **Neon branch** (free, instant
  copy-on-write branch of the same project) rather than standing up a whole second environment.
- The docker-compose Postgres is never pushed anywhere — "pushing the docker Postgres" isn't a thing
  that happens; the deployed backend connects to Neon via `DATABASE_URL`, full stop.

### Database & Vector Store — decided
- **Neon** (serverless Postgres, free tier). Chosen over Render's free Postgres because Render's free
  Postgres **expires after 90 days** (a hard trap for a project that needs to still be running at
  defense/demo time); Neon's free tier does not expire.
- **Vector store = the `pgvector` extension inside this same Neon database.** Not a separate decision,
  not a separate service — Neon's free tier supports `CREATE EXTENSION vector` directly (standard
  Postgres extension, enabled per-project in the Neon console or via migration). This avoids running
  or paying for Pinecone/Weaviate/Qdrant/a second Postgres just for embeddings.
- Fallback only if Neon's extension support ever changes: **Supabase** free tier (also Postgres +
  `pgvector`). Not needed unless Neon breaks this — don't build against both.

### Backend Hosting — decided: Render
- **Render** free web service, not Fly.io. Reasoning: Render's free web service tier has no credit
  card requirement and a simpler deploy model (connect the GitHub repo, point it at
  `Implementation/backend` as the root directory, it builds from `pyproject.toml`/a `Dockerfile`);
  Fly.io's free allowance requires a card on file and its CLI-based deploy flow is more setup for no
  MVP benefit here.
- Accepted caveat: Render's free tier spins the service down after ~15 minutes of inactivity, so the
  first request after idle has a cold start (tens of seconds). This is a documented MVP trade-off, not
  a bug to solve — worth mentioning to evaluators rather than paying to remove it.
- **Migrations on deploy**: use Render's "pre-deploy command" (or a build-step script) to run
  `poetry run alembic upgrade head` against `DATABASE_URL` before the new instance serves traffic —
  don't run migrations by hand against production.

### Frontend Hosting — decided: Vercel
- **Vercel** free tier, root directory set to `Implementation/frontend`. Zero-config for a Vite/React
  app, generous free tier, no reason to consider an alternative here.

### File Storage — decided
- Google Drive API, per-user (BYOS, §3.1 of the spec) for receipts. **No app-side object storage
  (no S3/R2/Cloudinary etc.) exists or is needed** — statement/CSV/image bytes are processed in memory
  per request and discarded; only Drive file references persist.

### LLM — decided
- Gemini free-tier API key via `litellm`, per the fallback cascade already in `llm_service.py`
  (§5.3 of the spec). No secondary LLM provider needed for MVP.

### Secrets — decided
- Platform-native env var configuration (Vercel project settings, Render environment group). No
  dedicated secrets manager (Vault, AWS Secrets Manager, etc.) — unjustified complexity at this scale.

### Explicitly decided *against*, for MVP (avoid scope creep here)
- **Transactional email** (verification emails, password reset): none for MVP. Registration/login is
  plain email+password with no email-based flows. Add this later only if a real deployed user base
  needs self-service password recovery.
- **Custom domain**: none — use the platform-provided subdomains (`*.vercel.app`, `*.onrender.com`).
  Buying a domain is a cost with zero MVP benefit.
- **Dedicated monitoring/error tracking** (Sentry, Datadog, etc.): none — Render/Vercel's built-in
  logs are enough to debug an MVP. Sentry's free tier is a cheap addition later if production
  debugging becomes genuinely painful, not a day-one requirement.
- **CI**: GitHub Actions running `poetry install && poetry run pytest` on push — free for the repo
  tier this project will use, and already justified in §5.

## 7. Milestone Roadmap

1. **M1 — Foundations + Auth + Drive** (B0–B1.5): migrations running, seed data loaded, users can
   register/login, Google Drive BYOS connection working end-to-end.
2. **M2 — Ingestion** (B2 + F0–F1): multi-file upload (incl. images) and manual entry both work
   end-to-end, land in the DB as pending transactions; receipts can attach to a connected Drive account.
3. **M3 — Review** (B3 + F2): human-in-the-loop approval flow fully functional.
4. **M4 — Computation** (B4 + F3): the tax engine, tested against hand-computed scenarios, wired to a
   dashboard showing the real breakdown. **This is the point at which the system does its core job.**
5. **M5 — Reporting** (B5 + F4 report half): downloadable self-assessment report.
6. **M6 — Advisor** (B6 + F4 advisor half): RAG-based Q&A. Lowest priority — cut first if time runs
   short, since M1–M5 alone is a complete, defensible MVP per the spec's scope.

## 8. Immediate Next Steps (first tasks to actually start on)

1. `git init` + `.gitignore` + move/gitignore the sample statement files in `scripts/`.
2. Alembic wiring + initial migration + category seeding (B0.2–B0.3).
3. Image ingestion branch in `parsing.py` + its tests (B2.13) — the specific feature requested earlier.
4. Google Drive OAuth connection + `DriveService` wrapper (B1.5) — the BYOS security feature, and a
   prerequisite for receipts.
5. Tax computation engine module + its hand-computed test scenarios (B4.19–20) — the highest-value,
   most independently-buildable piece, and can proceed in parallel with auth/ingestion/Drive work since
   it only needs a list of transaction-like objects, not the real API.
