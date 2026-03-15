"""
FastAPI application entry point.

Lifespan handles startup/shutdown (DB table creation is a temporary
convenience — Alembic is the real migration path).
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import setup_logging, get_logger
from app.db.base import Base
from app.db.session import engine
from app.routes import health, jobs


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    log = get_logger("startup")
    log.info("starting applybot api")

    # Temporary: ensure tables exist even without running Alembic.
    # Safe to remove once you always run `alembic upgrade head` before starting.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()
    log.info("shutdown complete")


app = FastAPI(
    title="applybot",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
