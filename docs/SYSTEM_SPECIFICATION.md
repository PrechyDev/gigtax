# GigTax — System Specification (MVP)

> Working name: **GigTax** (code/docker use this name). Some docs refer to "TaxEase NG" — treat these as
> the same product; do not hard-code the name into anything that would be painful to rename later
> (page titles, user-facing strings should live in one config/constants location).

## 1. Purpose & Problem Statement

Nigeria's Nigeria Tax Act (NTA) 2025 requires taxpayers under the **Direct Assessment** regime —
freelancers, remote/platform workers, content creators, digital vendors, sole traders whose income is
"ascertainable" (traceable via bank/digital payments) — to self-compute their Personal Income Tax
liability. These taxpayers have no employer withholding (no PAYE) and typically no accountant.
Existing platforms (FIRS TaxPro Max, state IRS portals) handle registration/filing/payment, but not
*figuring out what to file*.

GigTax closes that gap: it ingests a user's financial records (bank statements, receipts, handwritten
notes, manual entries), classifies income/expenses against NTA 2025 rules with AI assistance (always
reviewed/approved by the user), runs a deterministic tax computation engine, and produces a
self-assessment report plus plain-language AI guidance.

## 2. Target Users & Scope

**In scope:** individuals under Direct Assessment with ascertainable income — freelancers, remote
workers, creators, digital vendors, sole traders. Tax type: **Personal Income Tax only**.

**Explicitly out of scope:** PAYE employees (tax already withheld), companies/CIT, VAT, Capital Gains
Tax as a standalone flow, Presumptive Tax regime (untraceable/cash-based informal income — NTA 2025
s.29).

## 3. Functional Requirements

### 3.1 Onboarding, Profile & Storage Connection
- Register/login (email + password).
- Profile: name, occupation type, state of residence, tax year, home-office flag/percentage.
- **Google Drive connection (BYOS — Bring Your Own Storage) — MVP requirement, not deferred.** This
  is the project's core privacy story, so it belongs in the MVP rather than after it:
  - User clicks "Connect Google Drive"; backend redirects to Google's OAuth consent screen requesting
    only the **`drive.file`** scope — the narrowest Drive scope, granting the app access *only* to
    files/folders it itself creates, never the user's existing Drive contents. This scope does not
    require Google's full app-verification review at small scale (a "Google hasn't verified this app"
    click-through screen is expected and fine for a thesis-stage MVP with a handful of real users).
  - On consent, backend exchanges the auth code for tokens (`access_type=offline` to get a refresh
    token), encrypts the refresh token at rest (e.g. `cryptography.fernet` with a server-side key —
    never store it in plaintext), and creates a dedicated app folder (e.g. "GigTax Documents") in the
    user's own Drive on first connection.
  - All receipts and any raw source documents the user chooses to keep land in that folder via the
    Drive API; the backend stores only the returned Drive **file ID** (in `storage_path`), never the
    file bytes. This is why `Receipt.storage_path` and `StatementUpload.storage_path` already exist as
    reference fields rather than blob columns.
  - Uploading a receipt without a connected Drive account should prompt the user to connect first
    (graceful, not a hard blocker elsewhere in the app — statement parsing and manual entry work
    without Drive at all, since raw statement bytes are processed in memory and discarded regardless,
    per the existing PII-handling rule).

### 3.2 Data Ingestion — **updated in this round**
The system must accept, per upload action, **multiple files at once**, in any mix of:
- **CSV** (`pandas`)
- **Excel** (`.xls`/`.xlsx`, `pandas`/`openpyxl`)
- **PDF** — text-based or scanned (tiered fallback: `pdfplumber` → `pymupdf` → Gemini Vision)
- **Images** (`.jpg`/`.jpeg`/`.png`, and ideally `.heic` if a cheap conversion path exists) — e.g. a
  photo of a handwritten ledger of income/expenses. Images have **no reliable local-parsing path**
  (Tesseract OCR was already tried and abandoned for this project — see
  `docs/ai_categorization_architecture.md` — it hallucinated digits on real documents), so **every
  image is routed straight to Gemini Vision** for extraction. No pdfplumber/pymupdf attempt applies to
  images.
- Each file in a multi-file upload is processed and tracked independently (own `StatementUpload` row,
  own parsing status) so one bad file doesn't fail the whole batch.
- **Manual entry**: a form-based path to add a single income or expense record directly (date,
  description, amount, direction, category), bypassing parsing entirely. This is both a first-class
  input method and the fallback when extraction is incomplete or wrong.
- Password-protected PDFs: parsing raises `PasswordRequiredError` → API responds `423 Locked` →
  frontend prompts for a password in a modal, resubmits, password kept in memory only, never logged
  (contract already defined in `.agents/AGENTS.md`, not yet implemented at the API layer).

### 3.3 Review & Categorization (human-in-the-loop)
- Every parsed/manual record starts as a provisional entry with an AI-suggested category and
  confidence score.
- User must review each record in a queue: approve, correct the category, or reject.
- Custom rules: user-defined keyword→category mappings that apply automatically to recurring
  transactions (e.g. a specific client name → "Professional Gig Fees").
- **Only approved records ever reach the tax computation engine.** This is a hard invariant, not a UI
  nicety — it's how the system avoids being liable for AI mis-categorization.

### 3.4 Deductions, Reliefs & Receipts
- Expense records are validated against the NTA 2025 Section 20 ("wholly and exclusively to produce
  income") / Section 21 (disallowed) test via the category taxonomy (`db/seed_data/categories.json`
  already encodes this as a `tax_treatment` field per category).
- Statutory personal reliefs (Section 30(2)) are tracked as their own category classification, not as
  generic expenses: NHF, NHIS, Pension Reform Act contributions, owner-occupied home loan interest,
  life assurance premiums, and **rent relief = 20% of annual rent paid, capped at ₦500,000/year**.
- Receipts can be attached to a transaction for audit support (stored via user-controlled cloud
  storage, not centrally on the server — privacy-by-design).
- **Capital assets (equipment, laptops, cameras, vehicles) — mandatory MVP feature, not optional.**
  Treating a capital purchase as a normal 100%-deductible expense would inflate that year's deductions
  and understate tax owed, so these route to capital-allowance treatment instead: a fixed First
  Schedule Table I percentage of the original cost is deducted each year (straight-line) — Class 1
  10%/10yr (buildings, heavy transport), Class 2 20%/5yr (equipment, furniture — the common case for
  this app's users: laptops, cameras, general gear), Class 3 25%/4yr (vehicles, other capital
  expenditure) — until the asset is fully written down or disposed of, after which it contributes
  nothing further. An `Asset` row is created automatically whenever a transaction's category resolves
  to an Asset-classified category (whether from AI categorization, manual entry, or a human correcting
  a category during review), keeping the `assets` table always in sync with each transaction's current
  category.

### 3.5 Tax Computation Engine (deterministic — no LLM in the computation path)
See §6 for the exact model. Must be a pure, independently testable module — given a set of approved
transactions + reliefs, always produces the same number. This is the one place accuracy is
non-negotiable, so it has zero AI involvement at compute time (AI only assists earlier, at
categorization).

### 3.6 AI Tax Advisor (RAG) — built
- Plain-language Q&A grounded in real retrieval: the user's question is embedded
  (`gemini-embedding-001`, 3072-dim), matched by cosine distance against a `knowledge_chunks` table,
  and the top-k passages are injected as the LLM's only permitted context — the system prompt
  explicitly forbids answering from outside knowledge and tells the model to say so plainly (and
  suggest a licensed professional / State IRS) if the retrieved passages don't cover the question.
- Logged as `AIAdvisoryQuery` (question, `retrieved_sources` as a JSON list of real citations like
  `"Nigeria Tax Act 2025 (p.30)"`, answer, timestamp) for traceability.
- **Knowledge base is extensible by design, not a one-time seed.** `backend/scripts/ingest_document.py`
  extracts → chunks (page-bounded, so citations stay exact) → embeds → stores any PDF under a
  `source_title`; re-running it for the same title replaces that document's chunks. Currently loaded:
  the full Nigeria Tax Act 2025 gazette text. Adding a new supporting document later (a FIRS circular,
  a state IRS guide) is the same one command against whichever database is currently in use — no
  schema change, ever.
- No ANN index (ivfflat/HNSW) — exact cosine search is fast enough at this corpus size (one Act's
  worth of chunks); add one only if the knowledge base grows much larger.
- **Multi-turn memory, scoped to one chat session.** Gemini has no server-side conversation memory of
  its own — its "chat" abstraction is just resending prior turns as message history each call — so
  that's what's built: a client-held `session_id` (issued on the first message, passed back on every
  follow-up in the same chat) groups turns in `AIAdvisoryQuery`; the last few turns are loaded and
  passed as real message history, not a summarized recap. A bare follow-up ("is it capped?") also has
  its retrieval query enriched with the last couple of user turns' text, since otherwise it has no
  keywords of its own to embed well and retrieval silently drifts off-topic. Omitting `session_id`
  (or using a new one) starts a conversation with no memory of any other session.

### 3.7 Reporting & Filing Guidance
- Generate a downloadable self-assessment report: income summary, deductions, reliefs, stage-by-stage
  computation breakdown (with statutory citations), net tax payable.
- Link out to the relevant State IRS portal for actual filing (no filing automation in scope).

### 3.8 Tax Vault (stretch, not MVP-blocking)
- Estimate of projected annual liability + a suggested periodic set-aside amount, purely computed from
  existing `TaxComputation` data — no new inputs required.

## 4. Non-Functional Requirements

- **Accuracy**: tax computation must be verifiable against manually-computed scenarios; this is the
  system's core credibility requirement.
- **Security/Privacy**: PII sanitization (Presidio) on every document *before* any text leaves the
  process boundary to an LLM; raw bank statements are never persisted (in-memory processing only,
  per `.agents/AGENTS.md`); aligns with NDPA 2023. **BYOS (Bring Your Own Storage) via Google Drive is
  a core part of this story, not a nice-to-have**: the project never becomes a central repository of
  users' financial documents — receipts/documents live in each user's own Drive, under their own
  Google account's security and deletion control; the backend only ever holds a file reference and an
  encrypted OAuth refresh token, never the documents themselves.
- **Explainability**: every AI categorization is overridable; every tax computation shows its working.
- **Cost-consciousness**: this is a free-tier/student budget project (see §8) — every design decision
  should default to the cheapest viable option and avoid unnecessary paid infrastructure.
- **Modularity**: parsing / sanitization / categorization / computation / advisory are independent,
  separately testable modules with narrow interfaces — already the pattern in
  `backend/modules/ai_categorization/`; keep extending it, don't collapse layers together.
- **No overengineering**: MVP means the smallest correct implementation of each requirement above —
  no speculative abstraction for hypothetical future tax types (CIT/VAT), multi-tenancy, or
  configurability the MVP doesn't need.
- **Test-driven**: new business logic (especially the computation engine and the new ingestion paths)
  gets tests written alongside/before the implementation, following the existing
  `pytest` + `unittest.mock` pattern in `backend/tests/`.

## 5. System Architecture

### 5.1 Layers

```
 ┌─────────────────────────────────────────────────────────────┐
 │  Frontend (React SPA)                                        │
 │  upload/manual-entry UI · review queue · dashboard ·          │
 │  tax computation view · advisor chat · report download        │
 └───────────────────────────┬─────────────────────────────────┘
                              │ REST (JSON), multipart for uploads
 ┌───────────────────────────▼─────────────────────────────────┐
 │  API layer — FastAPI                                          │
 │  auth · statements · transactions · categories · computation · │
 │  advisory · reports                                            │
 └───────────────────────────┬─────────────────────────────────┘
        ┌─────────────────────┼─────────────────────────┐
        ▼                     ▼                         ▼
 ┌─────────────┐   ┌───────────────────────┐   ┌──────────────────┐
 │ AI pipeline  │   │ Tax computation engine │   │ RAG advisory      │
 │ parse→       │   │ (pure, deterministic,  │   │ (retrieval over   │
 │ sanitize→    │   │  no LLM at compute     │   │  NTA 2025 vector  │
 │ categorize   │   │  time)                 │   │  store)           │
 └─────┬───────┘   └───────────┬───────────┘   └────────┬─────────┘
       │                       │                          │
       ▼                       ▼                          ▼
 ┌───────────────────────────────────────────────────────────────┐
 │  PostgreSQL (users, statements, transactions, categories,      │
 │  custom rules, receipts refs, computations, reports, advisory  │
 │  logs)                                                          │
 └───────────────────────────────────────────────────────────────┘
       ▲
       │ metadata only — actual files
 ┌─────┴─────────────┐
 │ Google Drive (BYOS)│   user-controlled storage for receipts/raw docs
 └────────────────────┘
```

### 5.2 Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend framework | FastAPI (Python 3.10+) | already in place; async-friendly for file/LLM I/O |
| ORM / DB | SQLAlchemy 2.0 + PostgreSQL 15 | already in place |
| Migrations | Alembic | wired up — one migration per schema change, `alembic upgrade head` |
| Frontend | React + Vite + TypeScript | fast dev loop, free, matches report's committed choice |
| Styling | Tailwind CSS | fast to build with, no design system overhead for an MVP |
| Data fetching | TanStack Query (React Query) | handles loading/error/cache state without a heavy global store |
| Parsing | `pandas`, `pdfplumber`, `pymupdf` (local) → Gemini Vision (cloud fallback) | cost-tiered, already in place |
| PII sanitization | Microsoft Presidio | already in place, Nigeria-locale recognizers added |
| LLM routing | `litellm` + `instructor` | already in place — structured Pydantic output + model-agnostic routing |
| LLM provider | Google Gemini (free-tier API key) | zero-cost during development; see §5.3 for fallback cascade |
| Vector store (RAG) | `pgvector` extension on the existing Postgres instance | **no separate vector DB service** — avoids a second piece of paid/managed infra; Postgres already required. Local dev needs the `pgvector/pgvector:pg15` Docker image (stock `postgres:15` doesn't ship the extension) — Neon has it built in for the deployed app |
| Embeddings | `gemini-embedding-001` via `litellm` (3072-dim) | verified directly against the Gemini API before use — `text-embedding-004` (initially assumed) has been retired |
| Document storage | Google Drive API (user's own account/quota) | already decided in the report — privacy-by-design *and* zero storage cost to the project |
| Auth | FastAPI + `bcrypt` (direct, not `passlib` — avoids a known `passlib`/`bcrypt>=4.1` compatibility warning) + `pyjwt` | simplest standard approach, no third-party auth service needed for MVP |
| Drive integration | `google-auth`, `google-auth-oauthlib`, `google-api-python-client` (official Google libraries) + `cryptography` (Fernet) for encrypting stored refresh tokens | same GCP project as the Gemini API key can issue the OAuth client, one less thing to separately manage |

### 5.3 AI/LLM Strategy & Graceful Degradation

Current cascade, defined in `backend/services/llm_service.py` and reused as-is:

- **Default text/categorization model**: `gemini/gemini-3.5-flash` (`Settings.CATEGORIZATION_MODEL`)
- **Default vision model**: `gemini/gemini-3.5-flash`
- **On HTTP 429 / rate-limit / quota error**, `_execute_with_fallbacks` retries in order:
  1. `gemini/gemini-3.6-flash`
  2. `gemini/gemini-2.5-flash`
  3. `gemini/gemini-3.5-flash-lite`
- Non-rate-limit errors are not retried across models — they propagate immediately (a genuine parsing/
  schema error shouldn't be masked by silently trying four models).

**Rules going forward:**
- Any new AI-calling code (image ingestion, RAG advisory) must go through `llm_service`, not call
  `litellm`/`instructor` directly — one place to reason about the fallback chain and rate limits.
- Local-first: never call an LLM for something a local library can do reliably (CSV/Excel/text PDFs).
  Images and unreadable/scanned PDFs are the only cases that go straight to Gemini.
- **Do not spend free-tier quota in automated tests.** Unit tests mock `llm_service`/the
  `instructor` client (as `test_categorization.py` already does) — no test in the default `pytest` run
  may make a real network call. The existing `test_pipeline.py` CLI script (real calls, real sample
  files) stays a manual/opt-in tool, never part of CI or the default test suite.

### 5.4 Data Model

Existing ORM models (`backend/models/`) already cover the MVP's needs — see also
`docs/ai_categorization_architecture.md` for the categorization-specific shapes:

- `User` — credentials, occupation type, state of residence, tax year, home-office flag/%. **Needs
  three new fields for Drive BYOS**: `google_drive_connected` (bool), `google_refresh_token_encrypted`
  (string, Fernet-encrypted, never returned by any API response), `google_drive_folder_id` (the app's
  dedicated folder in the user's Drive, created on first connection).
- `StatementUpload` — one row per uploaded **file** (so a multi-file upload = multiple rows), tracks
  `ParsingStatus` (PENDING/PROCESSING/COMPLETED/FAILED) and `storage_path`. Needs a `source_type`
  distinction (`pdf`/`csv`/`excel`/`image`) so the review UI can show "extracted from photo" vs
  "extracted from statement."
- `Transaction` (polymorphic) → `IncomeRecord` / `ExpenseRecord` — `review_status`, `ai_category_id` vs
  `user_category_id`, `confidence_score`, `tax_treatment`.
- `CustomRule` — user keyword→category rules.
- `Receipt` — linked to a transaction, `storage_path` (Drive reference), `file_type`.
- `Category` — the NTA-2025-aligned taxonomy in `db/seed_data/categories.json` (Income / Expense /
  Relief / **Asset** / Unknown classifications), each with a `tax_treatment` enum-like string, plus
  `asset_class` (`class_1`/`class_2`/`class_3`) for Asset-classified rows only.
- `Asset` — a capital item (`cost`, `purchase_date`, `asset_class`, `disposed`/`disposed_date`),
  optionally linked to the `Transaction` it originated from. Created automatically whenever a
  transaction's category resolves to classification `Asset` — from AI ingestion, manual entry, or a
  human correcting a category during review (see §6 Stage 2b).
- `TaxComputation` — `total_income`, `total_deductions`, `total_reliefs`, `total_capital_allowances`,
  `taxable_income`, `estimated_tax_owed` per `tax_year`.
- `TaxReport` — generated report metadata (format, storage path).
- `AIAdvisoryQuery` — question, retrieved sources, answer, timestamp.

## 6. Tax Computation Model (deterministic, NTA 2025-accurate)

Five sequential stages, operating only on **approved** transactions for a given `tax_year` (plus, for
Stage 2b, every capital asset the user owns regardless of purchase year — see below):

**Stage 1 — Total Income** (NTA 2025 s.28)
Sum of all approved `IncomeRecord` amounts whose category `tax_treatment` is not
`excluded_from_progressive_tax` (i.e. exclude already-PAYE-taxed salary; it only affects bracket-
sanity-checking, not this system's liability calculation, since PAYE payers are out of scope) and not
`non_taxable`.

**Stage 2 — Total Allowable Deductions** (NTA 2025 ss.20–21)
Sum of approved `ExpenseRecord` amounts whose category `tax_treatment` is a deductible-expense type
(`100_percent_deductible`, `100_percent_deductible_home_office`, etc.), applying
`deductibility_percentage` where less than 100 (e.g. home-office-apportioned utilities). Categories
marked as disallowed (capital expenditure, private/domestic, fines) are excluded entirely — the
"wholly and exclusively to produce income" test (s.20) is enforced at the category level, not
re-derived per transaction. **Capital assets never appear here** — see Stage 2b.

**Stage 2b — Capital Allowances (NTA 2025 First Schedule Table I) — mandatory, not optional**
A capital item (laptop, camera, equipment, vehicle) is not a normal expense: deducting its full cost in
its purchase year would inflate that year's deductions and understate tax owed. Instead, any
transaction whose category classification is `Asset` creates a linked `Asset` row (cost, purchase date,
asset class) and is *excluded* from Stage 2 entirely. Each year, every non-disposed `Asset` the user
owns (bought this year or in an earlier one — depreciation spans years) contributes a straight-line
allowance:

| Class | Rate | Useful life | Covers |
|---|---|---|---|
| Class 1 | 10% | 10 years | Buildings, agriculture, masts, intangibles, heavy transport |
| Class 2 | 20% | 5 years | Plant/equipment, furniture, mining, other equipment — the common case here: laptops, cameras, general work gear |
| Class 3 | 25% | 4 years | Motor vehicles, software, other capital expenditure |

`allowance_this_year = cost × rate` for each year from acquisition until fully written down or disposed
of (whichever comes first); after that, the asset contributes nothing further. `total_capital_allowances
= Σ` this figure across every active asset for the requested tax year.

**Stage 3 — Statutory Reliefs** (NTA 2025 s.30(2))
Sum of approved records whose category classification is `Relief`:
- NHF, NHIS/health insurance, Pension Reform Act contributions, life assurance premiums,
  owner-occupied home-loan interest: full amount.
- **Rent relief**: `min(0.20 × annual_rent_paid, 500_000)`.

**Stage 4 — Chargeable Income and Net Tax**
```
chargeable_income = total_income − total_allowable_deductions − total_capital_allowances − total_reliefs
```
Apply the Fourth Schedule (s.58) progressive bands to `chargeable_income`, band by band:

| Band (₦) | Rate |
|---|---|
| First 800,000 | 0% |
| Next 2,200,000 (i.e. 800,001–3,000,000) | 15% |
| Next 9,000,000 (3,000,001–12,000,000) | 18% |
| Next 13,000,000 (12,000,001–25,000,000) | 21% |
| Next 25,000,000 (25,000,001–50,000,000) | 23% |
| Above 50,000,000 | 25% |

Special case: if the user's income is at or below the National Minimum Wage (s.58 / s.162(1)(t)), tax
is 0 regardless of the bands above — check this before running the band calculation, not as a side
effect of it.

`net_tax = Σ (amount in each band × that band's rate)`, stored as `estimated_tax_owed` on
`TaxComputation`, with a stage-by-stage breakdown returned to the frontend so the report can show its
work (income → deductions → reliefs → chargeable income → per-band tax → total), citing the relevant
sections.

This module must be pure Python, no I/O beyond receiving a list of approved transactions/reliefs and
returning a result object — trivially unit-testable against hand-computed scenarios (which is exactly
what the report's "accuracy testing" evaluation step requires).

## 7. Core Workflows

**A. File ingestion (multi-file, mixed types, including images)**
1. User selects one or more files (any mix of PDF/CSV/XLSX/JPG/PNG) in one upload action.
2. Frontend sends them as a multipart batch; backend creates one `StatementUpload` row per file,
   `PENDING`.
3. For each file, backend picks a path by extension:
   - `.csv`/`.xlsx` → `pandas` (no LLM call at all).
   - `.pdf` → `pdfplumber` → `pymupdf` → Gemini Vision (only if both local attempts fail or the PDF is
     a scan).
   - `.jpg`/`.jpeg`/`.png` → **straight to Gemini Vision** (no local attempt — there is no reliable
     local OCR path for handwritten notes; this project already ruled out Tesseract).
4. Extracted text (or vision-model transcription) is sanitized for PII, then categorized into
   `ParsedTransaction` records via `instructor`+`litellm`, using the existing category taxonomy +
   any user `CustomRule`s.
5. Each `StatementUpload` moves to `COMPLETED` (or `FAILED`, with the *other* files in the batch
   unaffected) and its transactions land in the review queue as `PENDING` review.
6. If a PDF is password-protected → `423 Locked` → frontend password modal → resubmit that one file
   only.

**B. Manual entry**
1. User opens "Add record," picks Income or Expense, fills date/description/amount/category.
2. Record is created directly with `review_status = APPROVED` (no AI categorization needed — the user
   is the source of truth for their own manual entry) or `PENDING` if a category doesn't need to be
   forced, whichever is decided during backend design.

**C. Review**
1. User works through pending transactions (from any source — file or manual), sees AI category +
   confidence, approves/corrects/rejects.
2. Custom rules can be created inline ("always categorize 'UBER *TRIP' as Transport") for future
   auto-application.

**D. Tax computation**
1. Triggered on demand (button) or automatically recomputed when the approved-transaction set for a
   tax year changes.
2. Runs the pure Stage 1–4 model in §6 against all `APPROVED` transactions for that `tax_year`, plus
   every `Asset` the user owns (not just ones purchased in that year — depreciation spans years) for
   Stage 2b's capital allowances.
3. Result persisted to `TaxComputation`, shown on the dashboard with full breakdown.

**E. Advisory (RAG)** — user asks a question → embed query → similarity search over the NTA 2025
`pgvector` store → inject top-k chunks as context → `llm_service.generate_text` → log to
`AIAdvisoryQuery`.

**F. Reporting** — assemble the latest `TaxComputation` + linked transactions/receipts into a
downloadable report (`TaxReport`), link to the user's State IRS portal for filing.

## 8. Budget & Free-Tier Constraints

This is a student project on free tiers throughout — every choice above was made with that in mind:
- **LLM**: Gemini free-tier API key, used sparingly (local parsing first), fallback cascade absorbs
  per-model rate limits instead of failing outright.
- **Vector store**: `pgvector` inside the already-required Postgres instance — no second managed
  service to pay for.
- **File storage**: Google Drive API against the *user's own* storage quota — zero storage cost to the
  project itself.
- **Hosting** (decided, see Build Plan §6 for full detail): **Vercel** (frontend), **Render** free web
  service (backend), **Neon** free-tier Postgres (database + `pgvector`) for the deployed app — the
  local `docker-compose` Postgres stays dev-only. Accept these tiers' limitations (Render cold starts
  after idle) as an MVP trade-off rather than paying to remove them.
- **Testing**: never burn LLM quota in automated/CI tests — mock everything by default (§5.3).

## 9. Out of Scope / Future Work

- Company Income Tax, VAT, Capital Gains Tax, Presumptive Tax regime.
- Filing automation (only guidance/link-out to state portals).
- Balancing charges/allowances on asset disposal (a disposed asset simply stops accruing further
  allowance — no gain-on-disposal adjustment is computed).
- Multi-currency / non-NGN handling beyond simple tagging.
- Tax Vault beyond a simple derived estimate.

## 10. Open Decisions (to confirm before/while building)

- Exact JWT/auth library and token lifetime policy.
- Whether manual entries default to `APPROVED` or still pass through a lightweight review step.
- `.heic` (iPhone photo format) support — worth a cheap server-side conversion, or defer and instruct
  users to share as JPEG/PNG?
