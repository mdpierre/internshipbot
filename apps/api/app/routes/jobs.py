"""
Jobs routes — thin handlers that validate, delegate, and respond.

Each endpoint follows the same pattern:
  1. Validate input (Pydantic does this automatically)
  2. Call a service function for business logic
  3. Persist via the injected DB session
  4. Return a consistent ApiResponse envelope

Error handling translates service-layer exceptions (httpx timeout,
HTTP errors, empty extractions) into appropriate HTTP status codes
with human-readable messages.
"""

from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Job
from app.db.session import get_db
from app.schemas.jobs import ApiResponse, JobCreate, JobResponse
from app.services import scraper

router = APIRouter()
log = get_logger(__name__)


@router.post("", response_model=ApiResponse[JobResponse], status_code=201)
async def create_job(
    body: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    url = str(body.url)

    # 1. Fetch the page HTML
    try:
        html = await scraper.fetch_page(url)
    except httpx.TimeoutException:
        log.warning("fetch_timeout", url=url)
        raise HTTPException(status_code=504, detail=f"Timed out fetching {url}")
    except httpx.HTTPStatusError as exc:
        log.warning("fetch_http_error", url=url, status=exc.response.status_code)
        raise HTTPException(
            status_code=502,
            detail=f"Upstream returned {exc.response.status_code} for {url}",
        )
    except httpx.RequestError as exc:
        log.warning("fetch_request_error", url=url, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Could not reach {url}")

    # 2. Extract readable text
    text = scraper.extract_text(html)
    if not text:
        raise HTTPException(status_code=422, detail="Page returned no extractable text")

    # 3. Detect which ATS this is from
    source = scraper.detect_source(url)

    # 4. Persist
    job = Job(
        url=url,
        source=source,
        raw_html=html,
        extracted_text=text,
        status="scraped",
    )
    db.add(job)
    await db.flush()       # assigns id + server defaults
    await db.refresh(job)  # load generated columns into the object

    log.info("job_created", job_id=str(job.id), source=source)
    return {"data": job}


@router.get("", response_model=ApiResponse[list[JobResponse]])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc())
    )
    jobs = result.scalars().all()
    return {"data": jobs}


@router.get("/{job_id}", response_model=ApiResponse[JobResponse])
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"data": job}
