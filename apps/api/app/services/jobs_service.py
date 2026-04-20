from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job
from app.schemas.jobs import JobBulkResult
from app.services.scraper import detect_source, extract_text, fetch_page


async def scrape_one(url: str, source_type: str, db: AsyncSession) -> JobBulkResult:
    existing = await db.execute(select(Job).where(Job.url == url))
    existing_job = existing.scalar_one_or_none()
    if existing_job is not None:
        return JobBulkResult(
            url=url,
            success=True,
            skipped=True,
            job=existing_job,
        )

    try:
        html = await fetch_page(url)
        text = extract_text(html)
        job = Job(
            url=url,
            source=detect_source(url),
            source_type=source_type,
            raw_html=html,
            extracted_text=text,
            status="scraped",
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)
        return JobBulkResult(url=url, success=True, job=job)
    except Exception as exc:
        return JobBulkResult(url=url, success=False, error=str(exc))
