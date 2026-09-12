# Deployment Guide

A concrete, step-by-step runbook for deploying GigTax on the free-tier stack already decided in
`BUILD_PLAN.md` §6: **Neon** (Postgres + pgvector) → **Render** (backend) → **Vercel** (frontend).
Follow it top to bottom for a first deploy; skip to the relevant section for a redeploy or fix.

Everything here targets the **free tier** of each platform. No credit card should be required for
any of the three signups below.

---

## 0. Before you start

You'll need, in hand:
- A GitHub account with this repo pushed to it (Render and Vercel both deploy from a connected repo).
- A Gemini API key (`GEMINI_API_KEY`) — already have one if local dev works.
- A Google Cloud OAuth client (`GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`) if you want Google Drive
  receipts to work in the deployed app — otherwise everything else works without it (see §4.1).

---

## 1. Database — Neon

1. Sign up at [neon.tech](https://neon.tech) (free tier, no card).
2. Create a project (any region close to Render's — Render's free tier runs in the US, so pick a
   US Neon region to minimize latency).
3. In the Neon SQL editor, run once:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
   This is required before the `knowledge_chunks` table's migration can succeed (it uses `pgvector`'s
   `Vector` column type — see `backend/models/knowledge_chunk.py`).
4. Copy the connection string Neon gives you (**"Connection string" → pick "Pooled connection"**).
   It looks like:
   ```
   postgresql://neondb_owner:AbC123@ep-cool-name-12345.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   Keep this — it's your backend's `DATABASE_URL` in §2.

Neon's free tier does not expire (unlike Render's free Postgres, which the project deliberately
avoided — see `BUILD_PLAN.md` §6 for why).

---

## 2. Backend — Render

### 2.1 Create the service
1. Sign up at [render.com](https://render.com) (free tier, no card).
2. **New → Web Service** → connect your GitHub repo.
3. **Root Directory**: `Implementation/backend`
4. **Runtime**: Python 3
5. **Build Command**:
   ```
   pip install poetry && poetry install --no-root && poetry run python -m spacy download en_core_web_lg
   ```
   **The `spacy download` step is easy to miss and the app will crash without it.** PII sanitization
   (`modules/ai_categorization/sanitization.py`) uses Presidio's default `AnalyzerEngine()`, which
   loads spaCy's `en_core_web_lg` model — a separate ~560MB download that `poetry install` does
   **not** fetch on its own (it's not a pip package, it's a spaCy model artifact). Locally this model
   was already present on the dev machine from an earlier manual step, so this gap wasn't obvious
   until checked directly. Without this build step, the first statement upload after deploy fails
   inside `get_analyzer()`.
   - If Render's free build times out or runs low on disk with the `lg` model, swap in
     `en_core_web_sm` (~13MB) instead — smaller and faster, at some cost to PERSON/LOCATION
     detection accuracy (format-based redaction — phone/email/card/IBAN — is unaffected either way,
     since that doesn't depend on the NLP model at all; see `ALWAYS_REDACTED_ENTITIES` in
     `sanitization.py`).
6. **Start Command** — runs migrations, then starts the server:
   ```
   poetry run alembic upgrade head && poetry run uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
   **Render's free tier has no "Pre-Deploy Command" field** (that's a paid-plan feature) — an
   earlier version of this guide assumed one existed and named it as the place migrations run. It
   doesn't exist on free, so a fresh deploy without this fix serves traffic against a database that
   was never migrated at all: every query 500s with `psycopg2.errors.UndefinedTable`, first noticed
   here when the scheduled cleanup job tried to touch a `transactions` table that didn't exist.
   Folding the migration into the Start Command instead means it runs before uvicorn starts,
   every single time the service starts — including after Render's free-tier idle spin-down, not
   just on a fresh deploy. `alembic upgrade head` is idempotent (a no-op once already at head), so
   this is safe to run on every cold start, at the cost of a few extra seconds before the app
   answers its first request after waking up.
7. **Environment variables** — add these in the Render dashboard (Environment tab), not in a
   committed file:

   | Key | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.12.10` (matches local dev — see `poetry run python --version`) |
   | `DATABASE_URL` | the Neon connection string from §1, exactly as copied (includes `?sslmode=require`) |
   | `GEMINI_API_KEY` | your key |
   | `JWT_SECRET_KEY` | a real random secret — generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"`. **Never reuse the local dev default.** |
   | `JWT_ALGORITHM` | `HS256` |
   | `JWT_EXPIRE_MINUTES` | `10080` |
   | `FERNET_SECRET_KEY` | generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — **a fresh one for prod, not your local dev key** (it encrypts Google refresh tokens at rest; losing/rotating it silently invalidates every connected user's Drive link) |
   | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | see §4.1 — leave blank to launch without Drive support |
   | `GOOGLE_REDIRECT_URI` | `https://<your-render-service>.onrender.com/auth/google/callback` |
   | `FRONTEND_URL` | `https://<your-vercel-app>.vercel.app` (set once you have it from §3 — used for both CORS and the post-OAuth redirect target) |

   Note: `DATABASE_URL` takes precedence over the discrete `POSTGRES_*` variables (see
   `core/config.py:SQLALCHEMY_DATABASE_URI`) — this project didn't originally support a single
   connection-string env var (only the five discrete Postgres fields used for local dev), which
   would have made pointing at Neon's SSL-required connection string awkward. That gap is fixed as
   part of writing this guide; don't set the discrete `POSTGRES_*` vars in Render at all.

8. Deploy. Watch the logs for the spaCy download completing during build, then for the Alembic
   migration succeeding right at the start of the run logs (before "Uvicorn running on...") before
   assuming it's live.

### 2.2 Known free-tier trade-off
Render's free web service spins down after ~15 minutes of inactivity. The first request after an
idle period takes tens of seconds (cold start) while it spins back up. This is a documented MVP
trade-off (see `BUILD_PLAN.md` §6) — worth mentioning to evaluators/users, not a bug to chase.

### 2.3 Seed the AI Advisor's knowledge base
The RAG advisor (`modules/advisory`) retrieves from `knowledge_chunks` — empty on a fresh Neon
database. Run once, from your local machine, pointed at the deployed database:
```
cd backend
DATABASE_URL="<your Neon connection string>" poetry run python -m scripts.ingest_document "<path-to-pdf>" --title "Nigeria Tax Act 2025"
```
(On Windows PowerShell: `$env:DATABASE_URL="..."; poetry run python -m scripts.ingest_document ...`)
Repeat for any other source document you want the advisor grounded in. Re-run with the same
`--title` any time a source document is updated — it replaces that document's existing chunks
rather than duplicating them.

---

## 3. Frontend — Vercel

1. Sign up at [vercel.com](https://vercel.com) (free tier, no card) and import the same GitHub repo.
2. **Root Directory**: `Implementation/frontend`
3. Framework preset: Vite (auto-detected).
4. **Environment variable**:

   | Key | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-render-service>.onrender.com` |

5. Deploy. `frontend/vercel.json` (added alongside this guide) rewrites all paths to `index.html` —
   without it, refreshing or directly opening a deep link like `/ledger` 404s, since this is a
   client-side-routed React Router app (`BrowserRouter` in `src/main.tsx`) and Vercel otherwise looks
   for a real `/ledger` file on disk.
6. Once deployed, go back to Render (§2.1) and set `FRONTEND_URL` to this Vercel URL, then
   redeploy the backend — CORS (`main.py`'s `CORSMiddleware`) only allows the one origin configured
   there, and the Google OAuth callback (§4) redirects back to this same URL.

---

## 4. Post-deploy configuration

### 4.1 Google Drive (optional, but needed for receipts)
If you skipped this at first deploy, the app runs fine without it — every feature except attaching
receipts works, and the Settings page just shows "Not Connected" with no way to connect.

1. In [Google Cloud Console](https://console.cloud.google.com), create (or reuse) a project.
2. **APIs & Services → OAuth consent screen**: External, add your own Google account as a test
   user (keeps it out of Google's verification review, fine for an MVP with few real users).
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**, type **Web
   application**.
4. **Authorized redirect URIs**: add exactly
   `https://<your-render-service>.onrender.com/auth/google/callback` (must match
   `GOOGLE_REDIRECT_URI` in Render byte-for-byte, including scheme and no trailing slash).
5. Scope needed at runtime: `https://www.googleapis.com/auth/drive.file` only (already hardcoded in
   `services/drive_service.py` — nothing to configure here, just don't grant broader scopes than
   this if the consent screen asks you to add scopes manually).
6. Copy the generated Client ID and Client Secret into Render's `GOOGLE_CLIENT_ID` /
   `GOOGLE_CLIENT_SECRET`, redeploy.
7. **Verify it actually works** — this can't be verified by automation, only by you, interactively:
   log into the deployed app, Settings → Integrations → Connect Drive, sign in with a real Google
   account, grant `drive.file`, confirm it redirects back showing "Connected," then upload a receipt
   from the Ledger and check it appears in a GigTax folder in that Google account's Drive.

### 4.2 CI (optional, recommended)
`BUILD_PLAN.md` §6 calls for a GitHub Actions workflow running `poetry install && poetry run pytest`
on push — free for this repo's tier and not yet added. Add `.github/workflows/backend-tests.yml` if
you want pushes to a PR to fail fast on a broken test rather than only finding out after a Render
deploy.

---

## 5. Redeploying after a change

- **Frontend-only change**: push to the connected branch — Vercel redeploys automatically.
- **Backend-only change**: push — Render redeploys automatically, running the migration step in the
  Start Command again (a no-op if there's nothing new to migrate).
- **New Alembic migration**: just push it — the Start Command's `alembic upgrade head` applies it on
  the very next start (deploy or cold-start wake-up alike). Never run a migration by hand against
  Neon from your machine as part of normal deploys; §2.3's manual `ingest_document` run is the one
  deliberate exception, since it's a content-seeding script, not a schema migration.
- **Rotated a secret** (`JWT_SECRET_KEY`, `FERNET_SECRET_KEY`): update it in Render's dashboard and
  manually trigger a redeploy (env var changes alone don't auto-redeploy on Render). Rotating
  `JWT_SECRET_KEY` invalidates every existing login token (users just log in again). Rotating
  `FERNET_SECRET_KEY` invalidates every stored Google Drive refresh token (connected users see
  "Not Connected" again and need to reconnect) — don't rotate it casually.

---

## 6. Troubleshooting checklist

| Symptom | Likely cause |
|---|---|
| Backend 500s on every request right after deploy, or logs show `psycopg2.errors.UndefinedTable: relation "..." does not exist` | The Start Command's `alembic upgrade head` isn't actually running (check it's really part of the Start Command, not left over as a separate Pre-Deploy Command field that doesn't exist on Render's free tier) — or `DATABASE_URL` is missing/wrong. As an immediate unblock, run migrations by hand once: `DATABASE_URL="<neon connection string>" poetry run alembic upgrade head` from your own machine |
| Backend 500s specifically on anything touching the AI Advisor | `CREATE EXTENSION vector;` (§1.3) was never run on Neon |
| First statement upload fails inside categorization | spaCy model wasn't downloaded during build (§2.1 step 5) |
| Frontend loads but every API call fails as a CORS error | `FRONTEND_URL` on Render doesn't exactly match the Vercel URL (scheme + host, no trailing slash) |
| Refreshing `/ledger` (or any non-root route) 404s on Vercel | `vercel.json` rewrite missing or not deployed |
| "Connect Drive" redirects to a Google error page | `GOOGLE_REDIRECT_URI` (Render env var) doesn't exactly match an Authorized redirect URI registered in Google Cloud Console |
| AI Advisor answers "I don't have information on that" for everything | `knowledge_chunks` is empty — run §2.3's ingestion step |
| First request after a while is very slow, then fine | Render free-tier cold start (§2.2) — not a bug |
