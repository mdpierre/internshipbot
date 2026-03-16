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
