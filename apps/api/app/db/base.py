"""
SQLAlchemy 2.0 declarative base.

All ORM models inherit from this Base.  Alembic's env.py imports
Base.metadata so autogenerate can diff models against the real DB.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
