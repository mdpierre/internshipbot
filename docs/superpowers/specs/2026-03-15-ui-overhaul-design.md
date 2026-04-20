# UI Overhaul + Markdown File Watcher — Design Spec
**Date:** 2026-03-15
**Status:** Approved

---

## Context

The current applybot UI is read-only: there is no way to submit job URLs from the browser, no job detail view, and no dashboard stats. Jobs must be added via `curl`. This spec covers a full UI overhaul plus a new markdown file watcher feature that lets users maintain a `.md` file of job links and have applybot automatically scrape new ones as they appear.

---

## Decisions Made

| Decision | Choice |
|---|---|
| Overall layout | Dashboard-first: URL input + stats on home page |
| Bulk input UX | Smart textarea — auto-detects URL count, button updates to "Scrape N URLs" |
| Job detail | Slide-up drawer — shows extracted text, open link, delete |
| MD watcher notification | Live syncing indicator with progress bar |
| MD URL formats | Bare URLs and standard markdown links `[text](url)` |
| MD file source | Both: configured watched path (persistent) + one-off file upload from UI |

---

## Architecture

### Data model clarification

The `jobs` table has two distinct "source" concepts that must both be tracked:

| Column | Values | Meaning |
|---|---|---|
| `source` (existing) | `"greenhouse"`, `"lever"`, `"unknown"` | Which ATS the URL belongs to (detected by URL pattern) |
| `source_type` (new) | `"manual"`, `"md"` | How the job was submitted (manually via UI/API, or via markdown file) |

These are separate columns. The Alembic migration adds `source_type VARCHAR(16) NOT NULL DEFAULT 'manual'` to the `jobs` table.

The frontend `Job` interface is updated to include both:
```typescript
interface Job {
  id: string
  url: string
  source: string        // "greenhouse" | "lever" | "unknown"
  source_type: string   // "manual" | "md"
  status: string
  extracted_text: string | null
  created_at: string
}
```

---

### Frontend changes (Next.js)

**`pages/index.tsx` — Home (rewritten)**
- Smart textarea input: counts newline-separated URLs, button label = `"Scrape"` (1 URL) or `"Scrape N URLs"` (N > 1)
- 4 stat cards: Total / Greenhouse / Lever / Unknown — labels match the backend string `"unknown"` (not "Other")
- Markdown File watcher section (see below)
- Recent jobs table (latest 20, no pagination on home page) with source badges and clickable rows
- Slide-up drawer rendered at page level, shared by all rows

**`pages/jobs.tsx` — Jobs list (updated)**
- Same table + drawer
- Filter tabs: All / Greenhouse / Lever / Unknown — **client-side filtering** (all jobs loaded, filtered in memory; pagination deferred)

**`components/JobDrawer.tsx` — new**
- Triggered by clicking any job row
- Shows: URL, `source` badge, `source_type` badge, status, date added, extracted text (scrollable, max 40vh)
- Actions: "open job" (external link, `target="_blank"`), "delete" with inline confirmation
- Delete calls `DELETE /jobs/{id}`, removes job from local state on success
- Dismisses on ✕ click or Escape key

**`components/MdWatcher.tsx` — new**
- Polls `GET /watcher/status` every 3 seconds
- Idle state: green dot, shows `path`, `last_synced_at`, `urls_found`
- Syncing state: purple pulsing dot, progress bar (`sync_progress.current / sync_progress.total`), border glow
- "change" link opens inline path editor (text input + save)
- "↑ upload new file" opens file picker → `POST /watcher/upload`
- Tracks `new_job_ids` from the status response to apply `md · new` badge to newly arrived rows

---

### Backend changes (FastAPI)

**`POST /jobs`** — updated for bulk with partial-failure support

New request model replaces `JobCreate`:
```python
class JobBulkCreate(BaseModel):
    urls: list[HttpUrl]   # 1 to 50 URLs
```

The existing `{ "url": "..." }` single-URL form is **removed** — callers pass `{ "urls": ["..."] }` even for one URL. The frontend and any callers are updated accordingly.

Response: **HTTP 207 Multi-Status** always, body is an array:
```json
[
  { "url": "https://...", "success": true, "job": { ...JobResponse } },
  { "url": "https://...", "success": false, "error": "Timed out fetching URL" },
  { "url": "https://...", "success": true, "job": { ...JobResponse }, "skipped": true }
]
```
- `skipped: true` means the URL already existed in the DB; the existing record is returned
- Scraping runs concurrently via `asyncio.gather(..., return_exceptions=True)`
- `source_type` defaults to `"manual"` for this endpoint

**`DELETE /jobs/{id}`** — new
- Deletes job by UUID, returns 204 No Content
- Returns 404 if not found

**`GET /jobs/stats`** — new
```json
{ "total": 12, "greenhouse": 5, "lever": 4, "unknown": 3 }
```
Field name is `"unknown"` (matches existing `detect_source()` output).

**`GET /jobs`** — updated to accept optional `limit` query param
- `GET /jobs?limit=20` returns the 20 most recent jobs (used by home page)
- `GET /jobs` with no limit returns all jobs (used by jobs list page, client-side filtered)
- Existing `ORDER BY created_at DESC` is unchanged

**`GET /watcher/status`** — new
```json
{
  "enabled": true,
  "path": "~/Documents/job-links.md",
  "state": "idle",
  "last_synced_at": "2026-03-15T12:00:00Z",
  "urls_found": 12,
  "sync_progress": { "current": 2, "total": 5 },
  "new_job_ids": ["uuid-1", "uuid-2"]
}
```
`new_job_ids` contains IDs of jobs created in the **most recent sync session**. Cleared at the start of each new sync. Frontend uses this to apply `md · new` badge.

**`PUT /watcher/config`** — new
- Body: `{ "path": "~/Documents/job-links.md" }`
- Persists to **`watcher.json`** in the project root (next to `.env`)
- Immediately starts watching the new path; stops watching the old one
- Returns updated status

**`POST /watcher/upload`** — new
- Accepts multipart file upload (`Content-Type: multipart/form-data`, field `file`)
- Parses all URLs from the uploaded `.md` content
- Triggers immediate scrape for URLs not already in DB, with `source_type='md'`
- Returns same 207 array format as `POST /jobs`

**`services/md_parser.py`** — new
```python
def extract_urls(content: str) -> list[str]:
    """Extract all unique HTTP(S) URLs from markdown content.
    Matches both bare URLs (https://...) and markdown links ([text](url)).
    """
```
- Markdown links matched first: `\[.*?\]\((https?://[^)]+)\)`
- Then bare URLs: `https?://[^\s\)\]]+`
- Deduplicates while preserving order

**`services/watcher.py`** — new, uses **`watchfiles`** library (async iterator, matches the existing async stack)

```python
async def start_watcher(path: str, db_session_factory):
    """Watch a markdown file and scrape new URLs when it changes."""
```

On **startup**, re-hydrates already-seen URLs by querying the DB for all jobs with `source_type='md'`, so it does not re-scrape existing entries after a server restart.

On **file change**: reads file, calls `md_parser.extract_urls()`, diffs against seen set, scrapes new URLs, stores with `source_type='md'`, updates watcher state in memory.

Watcher state (in-memory, acceptable for MVP — reset on restart except for the seen-URL set which is re-hydrated from DB):
```python
@dataclass
class WatcherState:
    enabled: bool = False
    path: str | None = None
    state: Literal["idle", "syncing"] = "idle"
    last_synced_at: datetime | None = None
    urls_found: int = 0
    sync_progress: dict = field(default_factory=lambda: {"current": 0, "total": 0})
    new_job_ids: list[str] = field(default_factory=list)
```

---

## DB Migration

One new migration (`alembic revision`):
```sql
ALTER TABLE jobs ADD COLUMN source_type VARCHAR(16) NOT NULL DEFAULT 'manual';
```

---

## Data Flow

### Manual URL submission
```
User pastes URLs → textarea counts lines → "Scrape N URLs" button
→ POST /jobs { "urls": [...] }
→ backend scrapes concurrently, deduplicates (skipped=true for existing)
→ 207 response array → frontend appends new/updated jobs, updates stat cards
```

### Markdown file watcher (background)
```
FastAPI lifespan starts watcher (reads watcher.json for path)
→ re-hydrates seen URLs from DB (source_type='md')
→ watchfiles watches configured path (async)
→ file changes → md_parser extracts URLs → diff against seen set
→ watcher state: { state: 'syncing', new_job_ids: [] }
→ scrape new URLs concurrently → store with source_type='md'
→ watcher state: { state: 'idle', new_job_ids: ['uuid-1', ...] }
→ frontend polls /watcher/status every 3s
→ syncing indicator shown; rows with IDs in new_job_ids get 'md · new' badge
```

### One-off MD upload
```
User clicks "↑ upload new file" → file picker
→ POST /watcher/upload (multipart)
→ parse → scrape new, skip existing → 207 response
→ same live syncing feedback via /watcher/status polling
```

---

## UI Details

### Job row badges
- `md` — small purple badge (`source_type === 'md'`)
- `md · new` — purple badge + left accent border (`source_type === 'md'` and `id` in `new_job_ids`)
- `manual` — dimmed, no background (visually quiet)

### Stat card labels
Cards show: **Total** / **Greenhouse** / **Lever** / **Unknown** (matching `source` values from DB exactly).

### Drawer
- Slides up from bottom of page on row click
- Extracted text scrollable, capped at 40vh
- Delete: click "delete" → inline "really delete?" confirmation → confirm calls `DELETE /jobs/{id}` → job removed from local state, drawer closed

### Syncing state
- Watcher card: purple border glow (`box-shadow: 0 0 0 1px #7c6aff22`)
- Purple pulsing dot, progress bar fills as each URL completes
- Stat card Total increments in real time as new jobs arrive (re-fetched after each poll showing new jobs)

---

## What's Out of Scope

- Authentication / multi-user support
- Pagination on home page (show latest 20) and jobs page (client-side filter only)
- LLM parsing of extracted text (Phase 2 of roadmap)
- Playwright auto-apply (Phase 3 of roadmap)
- Dark/light mode toggle (already dark-themed)
- Mobile responsiveness

---

## Verification

1. **Manual scrape — single**: paste 1 URL → button shows "Scrape" → click → job appears tagged `manual`
2. **Manual scrape — bulk**: paste 3 URLs → button shows "Scrape 3 URLs" → all 3 jobs appear
3. **Duplicate skip**: paste the same URL again → `skipped: true` in response, no duplicate in DB
4. **Partial failure**: paste 2 valid + 1 unreachable URL → 2 jobs created, 1 error entry returned, UI shows partial success
5. **Drawer open/close**: click job row → drawer slides up with extracted text, ✕ and Escape both close it
6. **Delete**: open drawer → delete → confirm → job gone from table and DB
7. **Stat cards**: verify Total / Greenhouse / Lever / Unknown update correctly as jobs are added
8. **Filter tabs on /jobs**: click "Greenhouse" → only greenhouse jobs shown (client-side)
9. **source and source_type both present**: check job response JSON includes both fields with correct values
10. **Watcher idle**: configure `~/job-links.md` → green dot, last synced time shown
11. **Watcher sync**: add new URL to watched file → within a few seconds: purple syncing dot, progress bar, job appears tagged `md · new`
12. **Watcher restart recovery**: restart API server → watcher re-hydrates from DB, does not re-scrape existing `md` jobs
13. **MD upload**: upload `.md` with 5 URLs (2 already in DB) → 3 new jobs, 2 skipped
14. **URL formats**: `https://jobs.greenhouse.io/123` and `[Stripe job](https://jobs.greenhouse.io/123)` both extracted correctly
15. **`watchfiles` integration**: watcher runs as async background task, does not block request handling
