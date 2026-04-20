# UI Overhaul + Markdown File Watcher Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the applybot UI to support in-browser job submission (bulk URL input), a job detail drawer, dashboard stats, and a background markdown file watcher that auto-scrapes new URLs when the file changes.

**Architecture:** Backend gains a shared `jobs_service.scrape_one` function (extracted from routes to avoid circular imports), bulk `POST /jobs`, `DELETE /jobs/{id}`, `GET /jobs/stats`, watcher CRUD endpoints, and two new services (`md_parser`, `watcher`). Frontend home page is rewritten as a dashboard with the URL input, stats, watcher control, and recent jobs table; the jobs list page gains filter tabs; a shared `JobDrawer` component handles detail + delete.

**Tech Stack:** FastAPI (async), SQLAlchemy 2 (asyncpg), Alembic, watchfiles, Next.js 14 (Pages Router), React 18, TypeScript 5.

**Spec:** `docs/superpowers/specs/2026-03-15-ui-overhaul-design.md`

---

## File Map

### Backend — new files
| File | Responsibility |
|---|---|
| `apps/api/app/services/jobs_service.py` | `scrape_one()` — core scrape-and-store logic, importable by routes and watcher without circular deps |
| `apps/api/app/services/md_parser.py` | Extract URLs from markdown content |
| `apps/api/app/services/watcher.py` | File-watch state, background task, seen-URL diffing |
| `apps/api/app/routes/watcher.py` | `/watcher/*` HTTP endpoints |
| `apps/api/alembic/versions/002_add_source_type.py` | Migration: add `source_type` column |

### Backend — modified files
| File | What changes |
|---|---|
| `apps/api/app/db/models.py` | Add `source_type: Mapped[str]` column |
| `apps/api/app/schemas/jobs.py` | Replace `JobCreate` with `JobBulkCreate`; add `source_type` to `JobResponse`; add `JobBulkResult`, `StatsResponse`, `WatcherStatus` |
| `apps/api/app/routes/jobs.py` | Rewrite `POST /jobs` (bulk, 207, sequential); add `DELETE /{id}`; add `GET /stats`; add `?limit` to `GET /` |
| `apps/api/app/db/session.py` | Export `session_factory` alias for use by background tasks |
| `apps/api/app/main.py` | Register watcher router; start/stop watcher background task in lifespan |
| `apps/api/requirements.txt` | Add `watchfiles>=0.21,<1` and `python-multipart>=0.0.9,<1` |

### Frontend — new files
| File | Responsibility |
|---|---|
| `apps/web/components/JobDrawer.tsx` | Slide-up drawer: detail view + inline delete confirm |
| `apps/web/components/MdWatcher.tsx` | Watcher status card: idle/syncing states, path config, file upload |

### Frontend — modified files
| File | What changes |
|---|---|
| `apps/web/styles/globals.css` | Add `.badge-md`, `.badge-manual`, `.btn`, `.card`, `.stat-card`, `.drawer-*`, `.watcher-*`, `.progress-bar`, `.filter-tab`, `.url-textarea` CSS |
| `apps/web/pages/index.tsx` | Full rewrite: smart textarea, stat cards, MdWatcher, recent jobs table + drawer |
| `apps/web/pages/jobs.tsx` | Add `source_type` to `Job` interface; add filter tabs (client-side); wire in `JobDrawer` |

---

## Chunk 1: Backend Data Layer

### Task 1: Add `source_type` to ORM model

**Files:**
- Modify: `apps/api/app/db/models.py`

- [ ] **Step 1: Add the column**

In `models.py`, add after the `source` column:

```python
source_type: Mapped[str] = mapped_column(
    String(16), nullable=False, default="manual", server_default="manual"
)
```

The full column order in `Job`: `id`, `url`, `source`, `source_type`, `raw_html`, `extracted_text`, `parsed_json`, `status`, `created_at`, `updated_at`.

- [ ] **Step 2: Verify the model loads**

```bash
cd apps/api
python -c "from app.db.models import Job; print(Job.__table__.columns.keys())"
```

Expected output includes `source_type` in the list.

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/db/models.py
git commit -m "feat(db): add source_type column to Job model"
```

---

### Task 2: Alembic migration for `source_type`

**Files:**
- Create: `apps/api/alembic/versions/002_add_source_type.py`

- [ ] **Step 1: Generate the migration**

```bash
cd apps/api
alembic revision -m "add_source_type"
```

Alembic creates a file with a random hex prefix like `a3f91b_add_source_type.py`. Open it and replace the `upgrade` and `downgrade` bodies with:

```python
import sqlalchemy as sa
from alembic import op

def upgrade() -> None:
    op.add_column(
        "jobs",
        sa.Column(
            "source_type",
            sa.String(16),
            nullable=False,
            server_default="manual",
        ),
    )

def downgrade() -> None:
    op.drop_column("jobs", "source_type")
```

- [ ] **Step 2: Run the migration**

```bash
cd apps/api
alembic upgrade head
```

Expected: `Running upgrade ... -> <revision>, add_source_type`

- [ ] **Step 3: Verify column exists in DB**

```bash
cd apps/api
python -c "
import asyncio
from sqlalchemy import text
from app.db.session import engine

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='jobs' AND column_name='source_type'\"))
        print(result.fetchall())

asyncio.run(check())
"
```

Expected: `[('source_type',)]`

- [ ] **Step 4: Commit**

```bash
git add apps/api/alembic/versions/
git commit -m "feat(db): migration 002 — add source_type to jobs"
```

---

### Task 3: Update Pydantic schemas

**Files:**
- Modify: `apps/api/app/schemas/jobs.py`

- [ ] **Step 1: Replace the file content**

```python
"""
Pydantic schemas for the /jobs and /watcher endpoints.

JobBulkCreate  — request body for POST /jobs (1–50 URLs)
JobBulkResult  — one entry in the 207 response array
JobResponse    — serialized Job for GET responses
StatsResponse  — response for GET /jobs/stats
WatcherStatus  — response for GET /watcher/status
WatcherConfig  — request body for PUT /watcher/config
ApiResponse    — generic {data, error} envelope (unchanged)
"""

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: str | None = None


class JobBulkCreate(BaseModel):
    urls: list[HttpUrl] = Field(min_length=1, max_length=50)


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    source: str
    source_type: str
    extracted_text: str | None
    parsed_json: dict | None
    status: str
    created_at: datetime
    updated_at: datetime


class JobBulkResult(BaseModel):
    url: str
    success: bool
    job: JobResponse | None = None
    skipped: bool = False
    error: str | None = None


class StatsResponse(BaseModel):
    total: int
    greenhouse: int
    lever: int
    unknown: int


class SyncProgress(BaseModel):
    current: int
    total: int


class WatcherStatus(BaseModel):
    enabled: bool
    path: str | None
    state: str  # "idle" | "syncing"
    last_synced_at: datetime | None
    urls_found: int
    sync_progress: SyncProgress
    new_job_ids: list[str]


class WatcherConfig(BaseModel):
    path: str
```

- [ ] **Step 2: Verify imports work**

```bash
cd apps/api
python -c "from app.schemas.jobs import JobBulkCreate, JobBulkResult, JobResponse, StatsResponse, WatcherStatus, WatcherConfig; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/schemas/jobs.py
git commit -m "feat(schemas): bulk schemas, WatcherStatus, StatsResponse, source_type in JobResponse"
```

---

## Chunk 2: Backend Jobs Service + Routes

### Task 4: Create `jobs_service` — shared scrape-one logic

This new service module is the single place that knows how to scrape a URL and persist a Job. Both the jobs route and the watcher service import from here, avoiding any circular dependency.

**Files:**
- Create: `apps/api/app/services/jobs_service.py`

- [ ] **Step 1: Check how `get_db` manages commits**

```bash
cat apps/api/app/db/session.py
```

Look for whether the session uses `async with db.begin()` (auto-commits on context exit) or requires an explicit `await db.commit()`. Note this for Step 2.

- [ ] **Step 2: Create `jobs_service.py`**

```python
"""
Jobs service — core scrape-and-store logic.

scrape_one() is the single entry point for scraping a URL and persisting
the result. It is called by the jobs route (bulk POST) and the watcher
service (background file watching). Keeping it here avoids circular imports
between routes and services.

The caller is responsible for committing the session after calling
scrape_one(). The function only flushes (assigns the DB-generated id)
so callers can batch multiple inserts before committing.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Job
from app.schemas.jobs import JobBulkResult, JobResponse
from app.services import scraper

log = get_logger(__name__)


async def scrape_one(url: str, source_type: str, db: AsyncSession) -> JobBulkResult:
    """
    Scrape a single URL, deduplicate, and persist with the given source_type.

    Returns a JobBulkResult. Does NOT commit — caller must commit the session.
    On duplicate URLs, returns the existing record with skipped=True.
    On scrape failure, returns success=False with an error message.
    """
    # Deduplication
    existing_result = await db.execute(select(Job).where(Job.url == url))
    existing_job = existing_result.scalar_one_or_none()
    if existing_job:
        log.info("job_skipped_duplicate", url=url)
        return JobBulkResult(
            url=url,
            success=True,
            skipped=True,
            job=JobResponse.model_validate(existing_job),
        )

    # Fetch
    try:
        html = await scraper.fetch_page(url)
    except httpx.TimeoutException:
        log.warning("fetch_timeout", url=url)
        return JobBulkResult(url=url, success=False, error=f"Timed out fetching {url}")
    except httpx.HTTPStatusError as exc:
        log.warning("fetch_http_error", url=url, status=exc.response.status_code)
        return JobBulkResult(url=url, success=False, error=f"Upstream returned {exc.response.status_code}")
    except httpx.RequestError as exc:
        log.warning("fetch_request_error", url=url, error=str(exc))
        return JobBulkResult(url=url, success=False, error=f"Could not reach {url}")

    # Extract text
    text = scraper.extract_text(html)
    if not text:
        return JobBulkResult(url=url, success=False, error="Page returned no extractable text")

    # Detect ATS source
    source = scraper.detect_source(url)

    # Persist (flush to get DB-assigned id; caller commits)
    job = Job(
        url=url,
        source=source,
        source_type=source_type,
        raw_html=html,
        extracted_text=text,
        status="scraped",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)

    log.info("job_created", job_id=str(job.id), source=source, source_type=source_type)
    return JobBulkResult(url=url, success=True, job=JobResponse.model_validate(job))
```

- [ ] **Step 3: Verify the module imports cleanly**

```bash
cd apps/api
python -c "from app.services.jobs_service import scrape_one; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/services/jobs_service.py
git commit -m "feat(services): add jobs_service.scrape_one — shared scrape-and-store logic"
```

---

### Task 5: Add `watchfiles`, `python-multipart` dependencies

**Files:**
- Modify: `apps/api/requirements.txt`

- [ ] **Step 1: Append new dependencies**

Add these two lines to `apps/api/requirements.txt`:

```
watchfiles>=0.21,<1
python-multipart>=0.0.9,<1
```

- [ ] **Step 2: Install**

```bash
cd apps/api && pip install watchfiles python-multipart
```

Expected: both packages install without errors.

- [ ] **Step 3: Commit**

```bash
git add apps/api/requirements.txt
git commit -m "deps(api): add watchfiles and python-multipart"
```

---

### Task 6: Rewrite jobs routes

**Files:**
- Modify: `apps/api/app/routes/jobs.py`

- [ ] **Step 1: Replace `jobs.py`**

```python
"""
Jobs routes — thin handlers that validate, delegate, and respond.

POST ""          — bulk scrape (1–50 URLs), 207 Multi-Status, sequential
GET  "/stats"    — counts by ATS source
GET  ""          — list all jobs, optional ?limit query param
GET  "/{job_id}" — single job by UUID
DELETE "/{job_id}" — delete a job, 204
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Job
from app.db.session import get_db
from app.schemas.jobs import (
    ApiResponse,
    JobBulkCreate,
    JobBulkResult,
    JobResponse,
    StatsResponse,
)
from app.services.jobs_service import scrape_one

router = APIRouter()
log = get_logger(__name__)


@router.post("", status_code=207)
async def create_jobs(
    body: JobBulkCreate,
    db: AsyncSession = Depends(get_db),
) -> list[JobBulkResult]:
    """
    Scrape URLs sequentially and return a 207 array.
    Sequential (not concurrent) to safely share the injected AsyncSession.
    For 1–50 URLs this is fast enough; HTTP latency dominates.
    """
    results = []
    for url in body.urls:
        result = await scrape_one(str(url), "manual", db)
        results.append(result)
    return results


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    total = await db.scalar(select(func.count()).select_from(Job))
    greenhouse = await db.scalar(
        select(func.count()).select_from(Job).where(Job.source == "greenhouse")
    )
    lever = await db.scalar(
        select(func.count()).select_from(Job).where(Job.source == "lever")
    )
    unknown = await db.scalar(
        select(func.count()).select_from(Job).where(Job.source == "unknown")
    )
    return StatsResponse(
        total=total or 0,
        greenhouse=greenhouse or 0,
        lever=lever or 0,
        unknown=unknown or 0,
    )


@router.get("", response_model=ApiResponse[list[JobResponse]])
async def list_jobs(
    limit: int | None = Query(default=None, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Job).order_by(Job.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {"data": jobs}


@router.get("/{job_id}", response_model=ApiResponse[JobResponse])
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": job}


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: UUID, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    log.info("job_deleted", job_id=str(job_id))
    return Response(status_code=204)
```

- [ ] **Step 2: Verify the API starts and all routes appear**

```bash
cd apps/api && uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. Confirm these routes are present:
- `POST /jobs`
- `GET /jobs/stats`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `DELETE /jobs/{job_id}`

- [ ] **Step 3: Smoke-test bulk scrape**

```bash
curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com"]}' | python3 -m json.tool
```

Expected: JSON array with one entry, either `"success": true` with a job object or `"success": false` with an error string.

- [ ] **Step 4: Smoke-test stats**

```bash
curl -s http://localhost:8000/jobs/stats | python3 -m json.tool
```

Expected: `{"total": N, "greenhouse": N, "lever": N, "unknown": N}`

- [ ] **Step 5: Smoke-test delete**

Get a job ID from `GET /jobs`, then:

```bash
curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/jobs/<uuid>
```

Expected: `204`

- [ ] **Step 6: Smoke-test 404 on missing job**

```bash
curl -s -o /dev/null -w "%{http_code}" -X DELETE http://localhost:8000/jobs/00000000-0000-0000-0000-000000000000
```

Expected: `404`

- [ ] **Step 7: Commit**

```bash
git add apps/api/app/routes/jobs.py
git commit -m "feat(api): bulk POST /jobs (207, sequential), DELETE, GET /stats, ?limit on list"
```

---

## Chunk 3: Backend Watcher Services

### Task 7: `md_parser` service

**Files:**
- Create: `apps/api/app/services/md_parser.py`

- [ ] **Step 1: Create the file**

```python
"""
Markdown URL parser.

Extracts all unique HTTP(S) URLs from markdown content.
Handles both bare URLs and standard markdown link syntax [text](url).
"""

import re

# Markdown links: [text](url) — matched first to avoid double-counting
_MD_LINK = re.compile(r"\[.*?\]\((https?://[^)\s]+)\)")
# Bare URLs — negative lookbehind excludes URLs already captured inside '('
_BARE_URL = re.compile(r"(?<!\()(https?://[^\s\)\]]+)")


def extract_urls(content: str) -> list[str]:
    """
    Return a deduplicated list of URLs found in `content`, preserving order.

    Markdown links are matched before bare URLs so the same URL is not
    counted twice when both patterns match the same string.
    """
    seen: set[str] = set()
    urls: list[str] = []

    for url in _MD_LINK.findall(content):
        if url not in seen:
            seen.add(url)
            urls.append(url)

    for url in _BARE_URL.findall(content):
        url = url.rstrip(".,;:!?")  # strip trailing punctuation
        if url not in seen:
            seen.add(url)
            urls.append(url)

    return urls
```

- [ ] **Step 2: Verify both URL formats are extracted and deduplicated**

```bash
cd apps/api
python -c "
from app.services.md_parser import extract_urls
md = '''
# Jobs

- [Stripe Engineer](https://jobs.greenhouse.io/stripe/123)
- https://jobs.lever.co/vercel/456
- [duplicate](https://jobs.greenhouse.io/stripe/123)
- bare duplicate: https://jobs.lever.co/vercel/456
'''
result = extract_urls(md)
print(result)
assert len(result) == 2, f'Expected 2, got {len(result)}'
assert 'https://jobs.greenhouse.io/stripe/123' in result
assert 'https://jobs.lever.co/vercel/456' in result
print('PASS')
"
```

Expected: `PASS`

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/services/md_parser.py
git commit -m "feat(services): add md_parser to extract URLs from markdown"
```

---

### Task 8: Export `session_factory` from `session.py`

The watcher background task creates its own DB sessions outside FastAPI's dependency injection. It needs direct access to the session factory.

**Files:**
- Modify: `apps/api/app/db/session.py`

- [ ] **Step 1: Read the current file**

```bash
cat apps/api/app/db/session.py
```

- [ ] **Step 2: Add `session_factory` export**

The session factory is assigned to `async_session` (the `async_sessionmaker` instance). Add an alias on the line directly after it:

```python
session_factory = async_session  # alias for background tasks outside FastAPI DI
```

Also note: `get_db` calls `await session.commit()` on success, so routes using `Depends(get_db)` do NOT need explicit `await db.commit()` calls — the dependency handles it.

- [ ] **Step 3: Verify the export works**

```bash
cd apps/api
python -c "from app.db.session import session_factory; print(type(session_factory)); print('ok')"
```

Expected: prints the sessionmaker type and `ok`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/app/db/session.py
git commit -m "feat(db): export session_factory alias for background task use"
```

---

### Task 9: Watcher service

**Files:**
- Create: `apps/api/app/services/watcher.py`

- [ ] **Step 1: Create the watcher service**

```python
"""
Markdown file watcher service.

Uses watchfiles (async iterator API) to watch a single markdown file.
On each change, extracts URLs via md_parser, diffs against already-seen
URLs, and scrapes new ones via jobs_service.scrape_one.

State is in-memory. seen_urls is re-hydrated from the DB on startup so
we don't re-scrape existing 'md' jobs after a server restart.
"""

import asyncio
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models import Job
from app.services import md_parser
from app.services.jobs_service import scrape_one

log = structlog.get_logger(__name__)

WATCHER_CONFIG_PATH = Path("watcher.json")


@dataclass
class WatcherState:
    enabled: bool = False
    path: str | None = None
    state: str = "idle"  # "idle" | "syncing"
    last_synced_at: datetime | None = None
    urls_found: int = 0
    sync_progress: dict = field(default_factory=lambda: {"current": 0, "total": 0})
    new_job_ids: list[str] = field(default_factory=list)
    # Internal — not exposed via API
    seen_urls: set[str] = field(default_factory=set)


# Module-level singleton — one watcher per process
state = WatcherState()
_watch_task: asyncio.Task | None = None


def load_config() -> str | None:
    """Read watched path from watcher.json if it exists."""
    if WATCHER_CONFIG_PATH.exists():
        try:
            return json.loads(WATCHER_CONFIG_PATH.read_text()).get("path")
        except Exception:
            return None
    return None


def save_config(path: str) -> None:
    """Persist watched path to watcher.json."""
    WATCHER_CONFIG_PATH.write_text(json.dumps({"path": path}))


async def hydrate_seen_urls(session_factory: async_sessionmaker) -> None:
    """
    On startup, load all URLs with source_type='md' from the DB into
    seen_urls so the watcher doesn't re-scrape them after a restart.
    """
    async with session_factory() as db:
        result = await db.execute(select(Job.url).where(Job.source_type == "md"))
        state.seen_urls = set(result.scalars().all())
    log.info("watcher_hydrated", seen_count=len(state.seen_urls))


async def _scrape_new_urls(
    urls: list[str], session_factory: async_sessionmaker
) -> list[str]:
    """
    Scrape new URLs via jobs_service.scrape_one, committing each in its
    own session. Returns a list of newly created job IDs.
    """
    new_ids: list[str] = []
    state.sync_progress = {"current": 0, "total": len(urls)}

    for i, url in enumerate(urls, 1):
        # Each URL gets its own session so failures don't roll back others
        async with session_factory() as db:
            async with db.begin():
                result = await scrape_one(url, "md", db)
                if result.success and result.job and not result.skipped:
                    new_ids.append(str(result.job.id))
                    state.seen_urls.add(url)
        state.sync_progress = {"current": i, "total": len(urls)}

    return new_ids


async def _watch_loop(path: str, session_factory: async_sessionmaker) -> None:
    """Background coroutine: watch file for changes, scrape new URLs."""
    from watchfiles import awatch

    expanded = os.path.expanduser(path)
    log.info("watcher_started", path=expanded)

    try:
        async for _ in awatch(expanded):
            log.info("watcher_file_changed", path=expanded)
            try:
                content = Path(expanded).read_text()
            except OSError as exc:
                log.warning("watcher_read_error", error=str(exc))
                continue

            all_urls = md_parser.extract_urls(content)
            new_urls = [u for u in all_urls if u not in state.seen_urls]
            state.urls_found = len(all_urls)

            if not new_urls:
                state.last_synced_at = datetime.now(timezone.utc)
                log.info("watcher_no_new_urls")
                continue

            # Begin sync
            state.state = "syncing"
            state.new_job_ids = []

            new_ids = await _scrape_new_urls(new_urls, session_factory)

            # Sync complete
            state.state = "idle"
            state.new_job_ids = new_ids
            state.last_synced_at = datetime.now(timezone.utc)
            log.info("watcher_sync_complete", new_jobs=len(new_ids))

    except asyncio.CancelledError:
        log.info("watcher_stopped")


async def start(session_factory: async_sessionmaker) -> None:
    """Start the file watcher. Called from FastAPI lifespan."""
    global _watch_task

    await hydrate_seen_urls(session_factory)

    path = load_config()
    if not path:
        log.info("watcher_no_config_skipping")
        return

    state.enabled = True
    state.path = path
    _watch_task = asyncio.create_task(_watch_loop(path, session_factory))


async def stop() -> None:
    """Cancel the watcher task. Called from FastAPI lifespan shutdown."""
    global _watch_task
    if _watch_task and not _watch_task.done():
        _watch_task.cancel()
        try:
            await _watch_task
        except asyncio.CancelledError:
            pass
    _watch_task = None
    state.enabled = False


async def reconfigure(path: str, session_factory: async_sessionmaker) -> None:
    """Switch the watcher to a new file path and restart the watch loop."""
    global _watch_task
    await stop()
    save_config(path)
    state.path = path
    state.enabled = True
    state.state = "idle"
    state.new_job_ids = []
    _watch_task = asyncio.create_task(_watch_loop(path, session_factory))
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
cd apps/api
python -c "from app.services import watcher; print('state:', watcher.state.enabled); print('ok')"
```

Expected: `state: False` and `ok`

- [ ] **Step 3: Commit**

```bash
git add apps/api/app/services/watcher.py
git commit -m "feat(services): add watcher with watchfiles, per-URL sessions, DB hydration on start"
```

---

### Task 10: Watcher routes + wire into `main.py`

**Files:**
- Create: `apps/api/app/routes/watcher.py`
- Modify: `apps/api/app/main.py`

- [ ] **Step 1: Create `routes/watcher.py`**

```python
"""
Watcher routes — control and status for the markdown file watcher.

GET  /watcher/status  — current watcher state
PUT  /watcher/config  — set or change the watched file path
POST /watcher/upload  — one-off .md file upload, scrape new URLs immediately
"""

import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, session_factory
from app.schemas.jobs import SyncProgress, WatcherConfig, WatcherStatus
from app.services import md_parser, watcher
from app.services.jobs_service import scrape_one

router = APIRouter()


@router.get("/status", response_model=WatcherStatus)
async def get_status() -> WatcherStatus:
    s = watcher.state
    return WatcherStatus(
        enabled=s.enabled,
        path=s.path,
        state=s.state,
        last_synced_at=s.last_synced_at,
        urls_found=s.urls_found,
        sync_progress=SyncProgress(**s.sync_progress),
        new_job_ids=s.new_job_ids,
    )


@router.put("/config", response_model=WatcherStatus)
async def update_config(body: WatcherConfig) -> WatcherStatus:
    expanded = os.path.expanduser(body.path)
    if not os.path.exists(expanded):
        raise HTTPException(status_code=422, detail=f"File not found: {expanded}")
    await watcher.reconfigure(body.path, session_factory)
    return await get_status()


@router.post("/upload", status_code=207)
async def upload_markdown(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> list:
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=422, detail="Only .md files are accepted")
    content = (await file.read()).decode("utf-8", errors="replace")
    urls = md_parser.extract_urls(content)
    if not urls:
        return []
    results = []
    new_ids = []
    for url in urls:
        result = await scrape_one(url, "md", db)
        results.append(result.model_dump())
        if result.success and result.job and not result.skipped:
            new_ids.append(str(result.job.id))
    # Update watcher state so frontend shows md · new badges for uploaded jobs
    if new_ids:
        watcher.state.new_job_ids = new_ids
    return results
```

- [ ] **Step 2: Update `main.py`**

Replace `apps/api/app/main.py` with:

```python
"""
FastAPI application entry point.

Lifespan handles startup/shutdown:
- DB table creation (temporary convenience — Alembic is the real path)
- Markdown file watcher background task
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging, get_logger
from app.db.base import Base
from app.db.session import engine, session_factory
from app.routes import health, jobs
from app.routes import watcher as watcher_routes
from app.services import watcher


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    log = get_logger("startup")
    log.info("starting applybot api")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await watcher.start(session_factory)

    yield

    await watcher.stop()
    await engine.dispose()
    log.info("shutdown complete")


app = FastAPI(title="applybot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(watcher_routes.router, prefix="/watcher", tags=["watcher"])
```

- [ ] **Step 3: Start the API and verify all routes appear**

```bash
cd apps/api && uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. Confirm:
- `GET /watcher/status`
- `PUT /watcher/config`
- `POST /watcher/upload`

- [ ] **Step 4: Smoke-test watcher status**

```bash
curl -s http://localhost:8000/watcher/status | python3 -m json.tool
```

Expected:
```json
{
  "enabled": false,
  "path": null,
  "state": "idle",
  "last_synced_at": null,
  "urls_found": 0,
  "sync_progress": {"current": 0, "total": 0},
  "new_job_ids": []
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/app/routes/watcher.py apps/api/app/main.py
git commit -m "feat(api): add watcher routes and wire into lifespan"
```

---

## Chunk 4: Frontend Styles + JobDrawer

### Task 11: Extend global CSS

**Files:**
- Modify: `apps/web/styles/globals.css`

- [ ] **Step 1: Append to `globals.css`**

Add to the end of the file:

```css
/* ── Additional CSS variables ─────────────────────────── */
:root {
  --accent-purple: #7c6aff;
  --accent-purple-hover: #6b58f0;
  --bg-input: #1a1a1a;
  --purple-bg: #7c6aff22;
}

/* ── Badges (additions) ───────────────────────────────── */
.badge-md {
  background: var(--purple-bg);
  color: var(--accent-purple);
}
.badge-manual {
  background: transparent;
  color: var(--text-muted);
}

/* ── Buttons ──────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border-radius: var(--radius);
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 0.15s;
}
.btn-primary { background: var(--accent-purple); color: #fff; }
.btn-primary:hover { background: var(--accent-purple-hover); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-danger { background: transparent; color: var(--error); border: 1px solid var(--error); }
.btn-danger:hover { background: #ef444422; }
.btn-ghost { background: transparent; color: var(--text-muted); }
.btn-ghost:hover { color: var(--text); }

/* ── Stat cards ───────────────────────────────────────── */
.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  text-align: center;
}
.stat-card__value { font-size: 1.75rem; font-weight: 700; line-height: 1; }
.stat-card__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ── Card ─────────────────────────────────────────────── */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 1rem;
}
.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.card__title {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 600;
}

/* ── Section label ────────────────────────────────────── */
.section-label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 0.75rem;
}

/* ── Table: clickable rows ────────────────────────────── */
.table-row-clickable { cursor: pointer; transition: background 0.1s; }
.table-row-clickable:hover { background: #161616; }
.table-row-new { border-left: 2px solid var(--accent-purple); background: #7c6aff08; }

/* ── Drawer ───────────────────────────────────────────── */
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 40;
}
.drawer {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  background: #111;
  border-top: 1px solid var(--border);
  border-radius: var(--radius) var(--radius) 0 0;
  padding: 1.25rem 1.5rem;
  z-index: 50;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}
.drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  flex-shrink: 0;
}
.drawer__meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-shrink: 0;
}
.drawer__text {
  overflow-y: auto;
  flex: 1;
  border-top: 1px solid var(--border);
  padding-top: 0.75rem;
  font-size: 0.875rem;
  line-height: 1.7;
  color: var(--text-muted);
  white-space: pre-wrap;
}
.drawer__actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
  flex-shrink: 0;
}

/* ── Watcher card ─────────────────────────────────────── */
.watcher-card { position: relative; }
.watcher-card--syncing { border-color: var(--accent-purple); box-shadow: 0 0 0 1px #7c6aff22; }
.watcher-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.watcher-dot--idle { background: var(--success); }
.watcher-dot--syncing { background: var(--accent-purple); animation: pulse 1s ease-in-out infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }

/* ── Progress bar ─────────────────────────────────────── */
.progress-bar { height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin: 0.5rem 0; }
.progress-bar__fill { height: 100%; background: var(--accent-purple); border-radius: 2px; transition: width 0.3s ease; }

/* ── Filter tabs ──────────────────────────────────────── */
.filter-tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 1rem; }
.filter-tab {
  padding: 0.5rem 1rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  background: none;
  border-top: none; border-left: none; border-right: none;
  transition: color 0.15s;
}
.filter-tab:hover { color: var(--text); }
.filter-tab--active { color: var(--accent-purple); border-bottom-color: var(--accent-purple); font-weight: 600; }

/* ── URL textarea ─────────────────────────────────────── */
.url-textarea {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 0.875rem;
  padding: 0.625rem 0.75rem;
  resize: vertical;
  min-height: 72px;
  font-family: inherit;
  line-height: 1.6;
}
.url-textarea:focus { outline: none; border-color: var(--accent-purple); }
.url-textarea::placeholder { color: var(--text-muted); }
```

- [ ] **Step 2: Start Next.js and check for CSS errors**

```bash
cd apps/web && npm run dev
```

Open `http://localhost:3000` — no console errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/styles/globals.css
git commit -m "feat(styles): drawer, watcher, stat-card, filter-tab, btn, url-textarea CSS"
```

---

### Task 12: `JobDrawer` component

**Files:**
- Create: `apps/web/components/JobDrawer.tsx`

- [ ] **Step 1: Create the component**

Note: The `Job` interface is exported from this file and imported by `index.tsx` and `jobs.tsx` — it is the single source of truth for the Job type.

```tsx
import { useEffect, useState } from "react";

export interface Job {
  id: string;
  url: string;
  source: string;
  source_type: string;
  status: string;
  extracted_text: string | null;
  created_at: string;
  updated_at: string;
}

interface Props {
  job: Job;
  newJobIds: string[];
  onClose: () => void;
  onDeleted: (id: string) => void;
}

export default function JobDrawer({ job, newJobIds, onClose, onDeleted }: Props) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  async function handleDelete() {
    setDeleting(true);
    try {
      const res = await fetch(`/api/jobs/${job.id}`, { method: "DELETE" });
      if (res.ok || res.status === 204) {
        onDeleted(job.id);
        onClose();
      }
    } finally {
      setDeleting(false);
    }
  }

  const isNew = newJobIds.includes(job.id);

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <div className="drawer">
        <div className="drawer__header">
          <div>
            <p style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: "0.25rem" }}>
              {isNew && <span style={{ color: "var(--accent-purple)", marginRight: "0.5rem" }}>● new</span>}
              {new Date(job.created_at).toLocaleDateString("en-US", {
                year: "numeric", month: "short", day: "numeric",
              })}
            </p>
            <p style={{
              fontSize: "0.875rem",
              color: "var(--text-muted)",
              maxWidth: 600,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}>
              {job.url}
            </p>
          </div>
          <button className="btn btn-ghost" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="drawer__meta">
          <span className={`badge badge-${job.source}`}>{job.source}</span>
          <span className={`badge badge-${job.source_type}`}>{job.source_type}</span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{job.status}</span>
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ marginLeft: "auto", fontSize: "0.8rem", color: "var(--accent-purple)" }}
          >
            ↗ open job
          </a>
        </div>

        <div className="drawer__text">
          {job.extracted_text ?? (
            <span style={{ color: "var(--text-muted)" }}>No extracted text available.</span>
          )}
        </div>

        <div className="drawer__actions">
          {!confirmDelete ? (
            <button className="btn btn-danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </button>
          ) : (
            <>
              <span style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>Really delete?</span>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                {deleting ? "Deleting…" : "Confirm"}
              </button>
              <button className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/JobDrawer.tsx
git commit -m "feat(ui): JobDrawer — slide-up detail view, Escape dismiss, inline delete confirm"
```

---

## Chunk 5: Frontend Pages

### Task 13: Update `jobs.tsx` with filter tabs and drawer

**Files:**
- Modify: `apps/web/pages/jobs.tsx`

- [ ] **Step 1: Replace `jobs.tsx`**

```tsx
import { useEffect, useState } from "react";
import JobDrawer, { Job } from "../components/JobDrawer";

type FilterSource = "all" | "greenhouse" | "lever" | "unknown";

const TABS: { label: string; value: FilterSource }[] = [
  { label: "All", value: "all" },
  { label: "Greenhouse", value: "greenhouse" },
  { label: "Lever", value: "lever" },
  { label: "Unknown", value: "unknown" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterSource>("all");
  const [activeJob, setActiveJob] = useState<Job | null>(null);

  useEffect(() => {
    fetch("/api/jobs")
      .then((res) => res.json())
      .then((json) => {
        if (json.error) setError(json.error);
        else setJobs(json.data ?? []);
      })
      .catch(() => setError("Failed to fetch jobs"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === "all" ? jobs : jobs.filter((j) => j.source === filter);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;
  if (error) return <p style={{ color: "var(--error)" }}>{error}</p>;

  return (
    <div>
      <h2 style={{ marginBottom: "1.25rem" }}>Jobs</h2>

      <div className="filter-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            className={`filter-tab${filter === tab.value ? " filter-tab--active" : ""}`}
            onClick={() => setFilter(tab.value)}
          >
            {tab.label}
            <span style={{ marginLeft: "0.4rem", color: "var(--text-muted)", fontWeight: 400 }}>
              ({tab.value === "all" ? jobs.length : jobs.filter((j) => j.source === tab.value).length})
            </span>
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <p style={{ color: "var(--text-muted)" }}>
          {jobs.length === 0
            ? "No jobs yet. Add some from the Home page."
            : "No jobs match this filter."}
        </p>
      ) : (
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Source</th>
                <th>Origin</th>
                <th>Status</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((job) => (
                <tr
                  key={job.id}
                  className="table-row-clickable"
                  onClick={() => setActiveJob(job)}
                >
                  <td style={{ maxWidth: 400 }}>
                    <span style={{
                      display: "block",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                      color: "var(--accent-purple)",
                    }}>
                      {job.url}
                    </span>
                  </td>
                  <td><span className={`badge badge-${job.source}`}>{job.source}</span></td>
                  <td><span className={`badge badge-${job.source_type}`}>{job.source_type}</span></td>
                  <td style={{ color: "var(--text-muted)" }}>{job.status}</td>
                  <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                    {new Date(job.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {activeJob && (
        <JobDrawer
          job={activeJob}
          newJobIds={[]}
          onClose={() => setActiveJob(null)}
          onDeleted={(id) => {
            setJobs((prev) => prev.filter((j) => j.id !== id));
            setActiveJob(null);
          }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/pages/jobs.tsx
git commit -m "feat(ui): jobs page — filter tabs (client-side), clickable rows, JobDrawer"
```

---

### Task 14: `MdWatcher` component

**Files:**
- Create: `apps/web/components/MdWatcher.tsx`

- [ ] **Step 1: Create the component**

```tsx
import { useEffect, useRef, useState } from "react";

interface SyncProgress { current: number; total: number; }

interface WatcherStatus {
  enabled: boolean;
  path: string | null;
  state: "idle" | "syncing";
  last_synced_at: string | null;
  urls_found: number;
  sync_progress: SyncProgress;
  new_job_ids: string[];
}

interface Props {
  onNewJobIds: (ids: string[]) => void;
  onJobsChanged: () => void;
}

export default function MdWatcher({ onNewJobIds, onJobsChanged }: Props) {
  const [status, setStatus] = useState<WatcherStatus | null>(null);
  const [editingPath, setEditingPath] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [savingPath, setSavingPath] = useState(false);
  const [pathError, setPathError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const prevIdsRef = useRef<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const res = await fetch("/api/watcher/status");
        if (!res.ok || cancelled) return;
        const data: WatcherStatus = await res.json();
        if (cancelled) return;
        setStatus(data);

        // Notify parent when new job IDs arrive that weren't there before
        const prev = new Set(prevIdsRef.current);
        const fresh = data.new_job_ids.filter((id) => !prev.has(id));
        if (fresh.length > 0) {
          onNewJobIds(data.new_job_ids);
          onJobsChanged();
        }
        prevIdsRef.current = data.new_job_ids;
      } catch {
        // Silently ignore poll failures
      }
    }

    poll();
    const interval = setInterval(poll, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [onNewJobIds, onJobsChanged]);

  async function savePath() {
    if (!pathInput.trim()) return;
    setSavingPath(true);
    setPathError(null);
    try {
      const res = await fetch("/api/watcher/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: pathInput.trim() }),
      });
      if (!res.ok) {
        const err = await res.json();
        setPathError(err.detail ?? "Failed to update path");
        return;
      }
      const updated: WatcherStatus = await res.json();
      setStatus(updated);
      setEditingPath(false);
    } finally {
      setSavingPath(false);
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      await fetch("/api/watcher/upload", { method: "POST", body: form });
      onJobsChanged();
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const isSyncing = status?.state === "syncing";
  const pct =
    status && status.sync_progress.total > 0
      ? Math.round((status.sync_progress.current / status.sync_progress.total) * 100)
      : 0;

  return (
    <div className={`card watcher-card${isSyncing ? " watcher-card--syncing" : ""}`}>
      <div className="card__header">
        <span className="card__title">Markdown File</span>
        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          <span className={`watcher-dot watcher-dot--${isSyncing ? "syncing" : "idle"}`} />
          <span style={{ fontSize: "0.75rem", color: isSyncing ? "var(--accent-purple)" : "var(--success)" }}>
            {isSyncing ? "syncing…" : status?.enabled ? "watching" : "not configured"}
          </span>
        </div>
      </div>

      {/* Path display / editor */}
      {!editingPath ? (
        <div style={{
          background: "var(--bg-input)",
          border: "1px solid var(--border)",
          borderRadius: "6px",
          padding: "0.5rem 0.75rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "0.5rem",
          fontSize: "0.875rem",
        }}>
          <span style={{ color: status?.path ? "var(--text)" : "var(--text-muted)" }}>
            {status?.path ?? "No file configured"}
          </span>
          <button
            className="btn btn-ghost"
            style={{ fontSize: "0.75rem", padding: "0.2rem 0.5rem" }}
            onClick={() => { setPathInput(status?.path ?? ""); setEditingPath(true); }}
          >
            {status?.path ? "change" : "set path"}
          </button>
        </div>
      ) : (
        <div style={{ marginBottom: "0.5rem" }}>
          <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.25rem" }}>
            <input
              type="text"
              value={pathInput}
              onChange={(e) => setPathInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") savePath();
                if (e.key === "Escape") setEditingPath(false);
              }}
              placeholder="~/Documents/job-links.md"
              style={{
                flex: 1,
                background: "var(--bg-input)",
                border: "1px solid var(--accent-purple)",
                borderRadius: "6px",
                color: "var(--text)",
                fontSize: "0.875rem",
                padding: "0.5rem 0.75rem",
              }}
              autoFocus
            />
            <button className="btn btn-primary" onClick={savePath} disabled={savingPath}>
              {savingPath ? "Saving…" : "Save"}
            </button>
            <button className="btn btn-ghost" onClick={() => setEditingPath(false)}>Cancel</button>
          </div>
          {pathError && <p style={{ color: "var(--error)", fontSize: "0.8rem" }}>{pathError}</p>}
        </div>
      )}

      {/* Syncing progress */}
      {isSyncing && (
        <>
          <div className="progress-bar">
            <div className="progress-bar__fill" style={{ width: `${pct}%` }} />
          </div>
          <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            Scraping {status!.sync_progress.current} of {status!.sync_progress.total} new URLs…
          </p>
        </>
      )}

      {/* Footer */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        marginTop: "0.5rem",
        fontSize: "0.8rem",
        color: "var(--text-muted)",
      }}>
        <span>
          {status?.last_synced_at
            ? `Last synced ${new Date(status.last_synced_at).toLocaleTimeString()} · ${status.urls_found} URLs found`
            : "Not yet synced"}
        </span>
        <label style={{ color: "var(--accent-purple)", cursor: "pointer" }}>
          {uploading ? "Uploading…" : "↑ upload .md file"}
          <input
            ref={fileInputRef}
            type="file"
            accept=".md"
            style={{ display: "none" }}
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add apps/web/components/MdWatcher.tsx
git commit -m "feat(ui): MdWatcher — 3s polling, path config, file upload, syncing progress"
```

---

### Task 15: Rewrite home page `index.tsx`

**Files:**
- Modify: `apps/web/pages/index.tsx`

- [ ] **Step 1: Replace `index.tsx`**

```tsx
import { useCallback, useEffect, useState } from "react";
import JobDrawer, { Job } from "../components/JobDrawer";
import MdWatcher from "../components/MdWatcher";

interface Stats { total: number; greenhouse: number; lever: number; unknown: number; }
interface BulkResult { url: string; success: boolean; job?: Job; skipped?: boolean; error?: string; }

function parseUrls(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.startsWith("http"));
}

export default function Home() {
  const [urlText, setUrlText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [newJobIds, setNewJobIds] = useState<string[]>([]);

  const urls = parseUrls(urlText);

  async function fetchStats() {
    try {
      const res = await fetch("/api/jobs/stats");
      if (res.ok) setStats(await res.json());
    } catch { /* ignore */ }
  }

  const fetchRecentJobs = useCallback(async () => {
    try {
      const res = await fetch("/api/jobs?limit=20");
      const json = await res.json();
      if (!json.error) setJobs(json.data ?? []);
    } catch { /* ignore */ }
    setLoadingJobs(false);
  }, []);

  useEffect(() => {
    fetchStats();
    fetchRecentJobs();
  }, [fetchRecentJobs]);

  async function handleScrape() {
    if (urls.length === 0) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urls }),
      });
      const results: BulkResult[] = await res.json();
      const created = results
        .filter((r) => r.success && r.job && !r.skipped)
        .map((r) => r.job!);
      const errors = results.filter((r) => !r.success);

      if (errors.length > 0) {
        setSubmitError(
          `${errors.length} URL(s) failed. ${created.length} added successfully.`
        );
      }
      if (created.length > 0) {
        setJobs((prev) => [...created, ...prev].slice(0, 20));
        await fetchStats();
        setUrlText("");
      }
    } catch {
      setSubmitError("Request failed. Is the API running?");
    } finally {
      setSubmitting(false);
    }
  }

  const STAT_ITEMS = [
    { label: "Total",      value: stats?.total      ?? "—", color: "var(--accent-purple)" },
    { label: "Greenhouse", value: stats?.greenhouse  ?? "—", color: "var(--success)" },
    { label: "Lever",      value: stats?.lever       ?? "—", color: "var(--accent)" },
    { label: "Unknown",    value: stats?.unknown     ?? "—", color: "var(--text-muted)" },
  ];

  return (
    <div>
      {/* URL input */}
      <div className="card">
        <div className="card__header">
          <span className="card__title">Add Jobs</span>
        </div>
        <textarea
          className="url-textarea"
          placeholder={"Paste one or more job URLs (one per line)\nhttps://jobs.greenhouse.io/...\nhttps://jobs.lever.co/..."}
          value={urlText}
          onChange={(e) => setUrlText(e.target.value)}
          rows={3}
        />
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "0.5rem" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {urls.length > 0 ? `${urls.length} URL${urls.length > 1 ? "s" : ""} detected` : ""}
          </span>
          <button
            className="btn btn-primary"
            disabled={urls.length === 0 || submitting}
            onClick={handleScrape}
          >
            {submitting ? "Scraping…" : urls.length > 1 ? `Scrape ${urls.length} URLs` : "Scrape"}
          </button>
        </div>
        {submitError && (
          <p style={{ color: "var(--error)", fontSize: "0.8rem", marginTop: "0.5rem" }}>{submitError}</p>
        )}
      </div>

      {/* Markdown file watcher */}
      <MdWatcher
        onNewJobIds={setNewJobIds}
        onJobsChanged={fetchRecentJobs}
      />

      {/* Stat cards */}
      <div className="stat-cards">
        {STAT_ITEMS.map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-card__value" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-card__label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Recent jobs table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)" }}>
          <span className="section-label" style={{ margin: 0 }}>Recent Jobs</span>
        </div>
        {loadingJobs ? (
          <p style={{ padding: "1rem", color: "var(--text-muted)" }}>Loading…</p>
        ) : jobs.length === 0 ? (
          <p style={{ padding: "1rem", color: "var(--text-muted)" }}>
            No jobs yet. Paste a URL above to get started.
          </p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Source</th>
                <th>Origin</th>
                <th>Added</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => {
                const isNew = newJobIds.includes(job.id);
                return (
                  <tr
                    key={job.id}
                    className={`table-row-clickable${isNew ? " table-row-new" : ""}`}
                    onClick={() => setActiveJob(job)}
                  >
                    <td style={{ maxWidth: 400 }}>
                      <span style={{
                        display: "block",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        color: "var(--accent-purple)",
                      }}>
                        {job.url}
                      </span>
                    </td>
                    <td><span className={`badge badge-${job.source}`}>{job.source}</span></td>
                    <td>
                      <span className={`badge badge-${job.source_type}`}>
                        {isNew ? `${job.source_type} · new` : job.source_type}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {activeJob && (
        <JobDrawer
          job={activeJob}
          newJobIds={newJobIds}
          onClose={() => setActiveJob(null)}
          onDeleted={(id) => {
            setJobs((prev) => prev.filter((j) => j.id !== id));
            fetchStats();
          }}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd apps/web && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Full end-to-end smoke test**

With API (`uvicorn app.main:app --reload`) and frontend (`npm run dev`) both running:

1. Open `http://localhost:3000`
2. Paste `https://example.com` → button shows "Scrape" → click → job appears in table tagged `manual`
3. Paste 2 URLs (one per line) → button shows "Scrape 2 URLs"
4. Click a job row → drawer slides up with extracted text → ✕ closes it
5. Open drawer → Delete → Confirm → job removed from table, stat cards update
6. Stat cards show correct Total / Greenhouse / Lever / Unknown counts
7. Create `~/test-jobs.md` with one URL, use `PUT /watcher/config` to point at it, add a second URL to the file → purple syncing dot, new job appears tagged `md · new`
8. Upload a `.md` file via "↑ upload .md file" → jobs from file appear in table

- [ ] **Step 4: Commit**

```bash
git add apps/web/pages/index.tsx
git commit -m "feat(ui): home page — smart URL input, stat cards, watcher, recent jobs + drawer"
```

---

## Final Verification

Run all 15 verification steps from the spec:

```
docs/superpowers/specs/2026-03-15-ui-overhaul-design.md — Verification section
```

All 15 must pass before marking this plan complete.
