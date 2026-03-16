"""
ORM models — one class per database table.

Design notes:
- UUIDs as primary keys: avoids sequential ID enumeration and is safe to
  expose in URLs.  server_default uses Postgres's gen_random_uuid().
- raw_html is nullable because we may choose not to store large HTML blobs
  in production.  extracted_text is nullable because scraping can fail.
- parsed_json (JSONB) will hold LLM-structured output in Phase 2.
- source is a plain string ("greenhouse", "lever", "unknown") rather than
  an enum so we can add new sources without a migration.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual", server_default="manual"
    )
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scraped")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} source={self.source} status={self.status}>"
