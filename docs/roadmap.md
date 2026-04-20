# Roadmap

## Phase 1 — Scrape & Ingest ← **current**

- [x] Monorepo scaffold (FastAPI + Next.js + Docker Compose)
- [x] Job model + Alembic migrations
- [x] `POST /jobs` — fetch URL, extract text, detect source, store
- [x] `GET /jobs` / `GET /jobs/{id}` — retrieve stored jobs
- [x] `/health` endpoint
- [ ] Basic error handling and consistent API response envelope

## Phase 2 — LLM Normalize

- [ ] Define a strict JSON schema for parsed job data (title, company, location, requirements, etc.)
- [ ] Call an LLM (OpenAI / local) with extracted text + schema
- [ ] Store result in `parsed_json` column
- [ ] `PATCH /jobs/{id}/parse` — trigger or re-trigger parsing
- [ ] Add confidence scores or validation flags

## Phase 3 — Playwright Auto-Apply

- [ ] Run model (DB + API)
- [ ] Greenhouse adapter — fill name, email, resume upload, custom questions
- [ ] Lever adapter — same pattern, different selectors
- [ ] Redis queue + worker process
- [ ] `POST /runs` — enqueue an application attempt
- [ ] Screenshot capture on success and failure
- [ ] Retry logic with backoff

## Phase 4 — Dashboard Polish

- [ ] Jobs list page with search, filter, sort
- [ ] Job detail page with raw text + parsed JSON side-by-side
- [ ] Runs list with status badges, timestamps, error previews
- [ ] Run detail page with screenshot viewer and full logs
- [ ] Retry button on failed runs
- [ ] Basic auth or local-only access guard

## Phase 5 — Hardening

- [ ] Rate limiting on scraper (respect robots.txt)
- [ ] Deduplication (same URL → update, not duplicate)
- [ ] Pagination on all list endpoints
- [ ] Integration tests (pytest + httpx TestClient)
- [ ] CI pipeline (GitHub Actions)
- [ ] Docker build for API + web
