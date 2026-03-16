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

WATCHER_CONFIG_PATH = Path(__file__).parent.parent.parent / "watcher.json"


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
