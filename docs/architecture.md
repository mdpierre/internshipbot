# Architecture

## Mental Model

```
User → POST /jobs {url}
         │
         ▼
   ┌─── Route (thin) ───┐
   │  validate input     │
   │  call service       │
   │  return response    │
   └─────────┬───────────┘
             │
             ▼
   ┌─── Service ─────────┐
   │  fetch_page(url)    │  ← httpx GET
   │  extract_text(html) │  ← BeautifulSoup
   │  detect_source(url) │  ← URL pattern match
   └─────────┬───────────┘
             │
             ▼
   ┌─── DB Layer ────────┐
   │  INSERT Job row     │  ← async SQLAlchemy + Postgres
   └─────────────────────┘
```

## Entities

### Job

A scraped job posting. Created when a URL is submitted.

| Field          | Type     | Purpose                                      |
|----------------|----------|----------------------------------------------|
| id             | UUID     | Primary key                                  |
| url            | String   | Original posting URL                         |
| source         | String   | ATS type: greenhouse, lever, or unknown      |
| raw_html       | Text     | Full HTML (nullable, for debugging)          |
| extracted_text | Text     | Cleaned readable text                        |
| parsed_json    | JSONB    | LLM-structured output (future)              |
| status         | String   | scraped → parsed → applied → failed          |
| created_at     | DateTime | Row creation time                            |
| updated_at     | DateTime | Last modification                            |

### Run (future)

An attempt to apply to a Job. One Job → many Runs.

| Field        | Type     | Purpose                              |
|--------------|----------|--------------------------------------|
| id           | UUID     | Primary key                          |
| job_id       | UUID     | FK → Job                             |
| status       | String   | pending, running, success, failed    |
| error        | Text     | Error message if failed              |
| screenshot   | String   | Path to screenshot file              |
| started_at   | DateTime | When the attempt began               |
| finished_at  | DateTime | When the attempt ended               |

## Layers

- **routes/** — HTTP endpoints. Validate input, delegate to services, return responses.
  Never contain business logic or raw SQL.
- **services/** — Business logic. Fetching pages, parsing HTML, calling LLMs.
  Pure functions where possible; receive a DB session when they need persistence.
- **db/** — Models (ORM classes), session management, migrations (Alembic).
- **schemas/** — Pydantic models defining request/response shapes.
  Separate from DB models so the public API contract is independent of storage details.
- **core/** — Config (env loading) and logging. Shared infrastructure.

## Why Adapters?

Greenhouse and Lever have different form structures. A site adapter encapsulates
the knowledge of how to fill out a specific ATS's application form. When we add
Playwright-based auto-apply, the scraper's `source` field determines which
adapter to invoke. Unknown sources get a generic adapter or are flagged
for manual application.

## Queueing (future)

The API should respond fast. Playwright-based applications take 10-30 seconds.
When we implement auto-apply, `POST /runs` will enqueue a task to Redis and
return immediately. A separate worker process picks up the task, runs the
Playwright session, and writes the result back. This keeps the API responsive.
