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
) -> list[JobBulkResult]:
    """
    Scrape URLs sequentially, one DB session per URL, and return a 207 array.
    Each URL gets its own session+transaction so a failure on URL N does not
    roll back successfully stored results for URLs 1..N-1.
    """
    from app.db.session import session_factory
    results = []
    for url in body.urls:
        async with session_factory() as db:
            async with db.begin():
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
