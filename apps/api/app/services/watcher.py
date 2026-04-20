from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.logging import get_logger
from app.schemas.jobs import SyncProgress, WatcherStatus

log = get_logger(__name__)


@dataclass
class WatcherState:
    enabled: bool = False
    path: str | None = None
    state: str = "idle"
    last_synced_at: datetime | None = None
    urls_found: int = 0
    sync_progress: SyncProgress = field(default_factory=lambda: SyncProgress(current=0, total=0))
    new_job_ids: list[str] = field(default_factory=list)


_state = WatcherState()
_session_factory: async_sessionmaker | None = None


async def start(session_factory: async_sessionmaker) -> None:
    global _session_factory
    _session_factory = session_factory
    log.info("watcher_started")


async def stop() -> None:
    log.info("watcher_stopped")


def get_status() -> WatcherStatus:
    return WatcherStatus(
        enabled=_state.enabled,
        path=_state.path,
        state=_state.state,
        last_synced_at=_state.last_synced_at,
        urls_found=_state.urls_found,
        sync_progress=_state.sync_progress,
        new_job_ids=_state.new_job_ids,
    )


def configure(path: str) -> WatcherStatus:
    _state.path = path
    _state.enabled = True
    return get_status()


def sync_now() -> WatcherStatus:
    _state.state = "idle"
    _state.last_synced_at = datetime.now(timezone.utc)
    return get_status()
