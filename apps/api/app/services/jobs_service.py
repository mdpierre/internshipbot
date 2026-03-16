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
