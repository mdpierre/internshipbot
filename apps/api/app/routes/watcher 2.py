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
