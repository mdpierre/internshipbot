"""
Alembic environment — configured for async SQLAlchemy.

Key points:
- We override sqlalchemy.url at runtime from our Settings object so the
  real connection string comes from .env, not hardcoded in alembic.ini.
- target_metadata points at Base.metadata so `--autogenerate` can diff
  our ORM models against the live database.
- run_async_migrations() uses asyncpg under the hood.
"""

import asyncio
import sys
from pathlib import Path
from logging.config import fileConfig

# Alembic runs from the alembic/ directory, but our app package lives one
# level up.  Add the api root to sys.path so "from app.…" imports work.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.base import Base

# Import all models here so Base.metadata is fully populated before
# Alembic inspects it.  Without this, autogenerate sees zero tables.
import app.db.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emits SQL without a live connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
