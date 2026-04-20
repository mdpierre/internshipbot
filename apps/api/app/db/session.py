"""
Async engine and session factory.

get_db() is an async generator designed for FastAPI's Depends() system:
each request gets its own session, which is committed on success or
rolled back on error, then always closed.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=(settings.environment == "development"),
    pool_pre_ping=True,
)

async_session = async_sessionmaker(engine, expire_on_commit=False)
session_factory = async_session  # alias for background tasks outside FastAPI DI


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session = async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
