# CLAUDE.md

## Project Overview

This repository is a local-first job application assistant centered on a FastAPI backend, a Next.js dashboard, and an Electron desktop shell.

Current v1 product shape:
- Assisted apply only.
- The backend is the source of truth for jobs, profile slots, resumes, and application session history.
- The dashboard manages profile data, job ingestion, and session review.
- A separate Chrome extension acts as the browser-side autofill worker and is expected to call the local backend.
- Playwright-driven autonomous applications are intentionally deferred.

Core workflow:
1. User adds job URLs or syncs markdown job sources.
2. Backend scrapes and stores jobs.
3. User manages one of exactly three profile slots: `profile_1`, `profile_2`, `profile_3`.
4. User uploads and parses a resume into a profile slot.
5. Extension creates an application session, requests a fill payload, autofills the live form, and reports events/results back.
6. Dashboard shows jobs, profiles, extension state, and application sessions.

## Repository Layout

```text
apps/api/       FastAPI backend, SQLAlchemy models, Alembic migrations, services
apps/web/       Next.js dashboard using the Pages Router
apps/desktop/   Electron shell for local desktop packaging
docs/           Architecture notes and roadmap
profiles/       Local-only PII storage area (gitignored)
```

Key backend routes:
- `/health`
- `/jobs`
- `/profiles`
- `/application-sessions`
- `/extension/config`
- `/watcher`

Key data entities:
- `Job`
- `ProfileSlot`
- `ProfileExperience`
- `ProfileEducation`
- `ApplicationSession`
- `ApplicationEvent`

## Local Development

### Prerequisites
- Docker
- Python 3.12+
- Node 18+

### Start infrastructure

```bash
docker compose up -d
```

### Run the API

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Run the dashboard

```bash
cd apps/web
npm install
npm run dev
```

### Run the desktop shell

```bash
cd apps/desktop
npm install
npm run dev
```

Notes:
- The dashboard proxies `/api/*` to `http://localhost:8000/*` through `apps/web/next.config.js`.
- The API seeds the three profile slots automatically on startup.
- The extension bootstrap endpoint is `GET /extension/config`.

## Product Constraints

These are intentional and should be preserved unless there is an explicit product decision to change them:

- Keep exactly three generic profile slots:
  - `profile_1`
  - `profile_2`
  - `profile_3`
- Keep the system local-first.
- Do not add cloud-only assumptions for core profile or resume workflows.
- Keep manual review and manual submission as the default behavior in v1.
- Do not reintroduce a second source of truth for profiles outside the backend.
- Job ingestion should remain useful even when extension autofill is not being used.

## Backend Conventions

- Keep route files thin.
- Put business logic in `apps/api/app/services/`.
- Keep API shapes in `apps/api/app/schemas/`.
- Keep persistence concerns in `apps/api/app/db/`.
- Use Alembic for schema changes.
- Maintain compatibility with Postgres as the primary database.
- Preserve the current session/event flow:
  1. create application session
  2. fetch payload
  3. send fill events
  4. send final result

When extending profiles:
- Update both the SQLAlchemy models and Pydantic schemas.
- Keep the extension payload flattened and stable where possible.
- Avoid making resume parsing a hard dependency for saving a profile.

## Frontend Conventions

- The dashboard uses the Next.js Pages Router, not the App Router.
- Preserve the current dark control-room visual direction unless the product direction changes.
- Reuse the existing shell and card system instead of adding disconnected page styles.
- Keep the dashboard functional without the desktop shell during development.
- Favor server-backed state over browser-only persistence for profile and session data.

## Desktop Shell Conventions

- Electron is a packaging layer, not the business logic layer.
- Backend data should live in the API datastore, not in Electron-only storage.
- Desktop onboarding should point users toward:
  - profile setup
  - resume upload/parse
  - extension connection
  - active slot selection

## Testing Checklist

When making changes in this repo, verify the relevant parts of the workflow:

- `GET /health` succeeds.
- `GET /profiles` returns the three seeded profile slots.
- `PUT /profiles/{slot}` saves updates.
- `POST /profiles/{slot}/resume` accepts a PDF upload.
- `POST /profiles/{slot}/parse-resume` returns parsed profile data.
- `GET /extension/config` returns a healthy local config.
- `POST /application-sessions` creates a session.
- `GET /application-sessions/{id}/payload` returns profile data for extension autofill.
- `POST /application-sessions/{id}/events` records field-level events.
- `POST /application-sessions/{id}/result` updates final session state.
- Dashboard pages still render:
  - `/`
  - `/profiles`
  - `/sessions`
  - `/jobs`

## Privacy And Safety

- Never commit `.env`, resume files, or personal profile data.
- Treat anything under local profile/resume storage as sensitive.
- This tool is for personal workflow assistance, not employer spam.
- Be cautious with automation features that could violate job platform terms.

## Useful Files

- `README.md`
- `docs/architecture.md`
- `apps/api/app/main.py`
- `apps/api/app/db/models.py`
- `apps/api/app/routes/profiles.py`
- `apps/api/app/routes/application_sessions.py`
- `apps/api/app/routes/extension.py`
- `apps/web/pages/index.tsx`
- `apps/web/pages/profiles.tsx`
- `apps/web/pages/sessions.tsx`
- `apps/desktop/main.js`
