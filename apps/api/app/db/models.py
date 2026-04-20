"""
ORM models for jobs, profile slots, and extension-driven application sessions.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from app.db.base import Base


class GUID(TypeDecorator):
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value if isinstance(value, uuid.UUID) else uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown")
    source_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="manual", server_default="manual"
    )
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scraped")

    application_sessions: Mapped[list["ApplicationSession"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Job {self.id} source={self.source} status={self.status}>"


class ProfileSlot(Base, TimestampMixin):
    __tablename__ = "profile_slots"

    slot: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    first_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    last_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    state: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    zip: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(255), nullable=False, default="United States")
    linkedin: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    website: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    github: Mapped[str] = mapped_column(String(2048), nullable=False, default="")

    target_title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    target_salary: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    work_authorization: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Yes - U.S. Citizen or Permanent Resident",
    )
    require_sponsorship: Mapped[str] = mapped_column(String(64), nullable=False, default="No")
    veteran: Mapped[str] = mapped_column(String(64), nullable=False, default="No")
    disability: Mapped[str] = mapped_column(String(64), nullable=False, default="Prefer not to say")
    gender: Mapped[str] = mapped_column(String(64), nullable=False, default="Prefer not to say")
    ethnicity: Mapped[str] = mapped_column(String(128), nullable=False, default="Prefer not to say")

    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")

    resume_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    resume_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    resume_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resume_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    experiences: Mapped[list["ProfileExperience"]] = relationship(
        back_populates="profile_slot",
        cascade="all, delete-orphan",
        order_by="ProfileExperience.sort_order",
    )
    educations: Mapped[list["ProfileEducation"]] = relationship(
        back_populates="profile_slot",
        cascade="all, delete-orphan",
        order_by="ProfileEducation.sort_order",
    )
    application_sessions: Mapped[list["ApplicationSession"]] = relationship(
        back_populates="profile_slot_ref",
    )


class ProfileExperience(Base):
    __tablename__ = "profile_experiences"
    __table_args__ = (UniqueConstraint("profile_slot_id", "sort_order", name="uq_profile_experience_order"),)

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_slot_id: Mapped[str] = mapped_column(
        ForeignKey("profile_slots.slot", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    employer: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    start_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    end_date: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    profile_slot: Mapped["ProfileSlot"] = relationship(back_populates="experiences")


class ProfileEducation(Base):
    __tablename__ = "profile_educations"
    __table_args__ = (UniqueConstraint("profile_slot_id", "sort_order", name="uq_profile_education_order"),)

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_slot_id: Mapped[str] = mapped_column(
        ForeignKey("profile_slots.slot", ondelete="CASCADE"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    school: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    degree: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    major: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    graduation_year: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    gpa: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    profile_slot: Mapped["ProfileSlot"] = relationship(back_populates="educations")


class ApplicationSession(Base, TimestampMixin):
    __tablename__ = "application_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    profile_slot: Mapped[str] = mapped_column(
        ForeignKey("profile_slots.slot", ondelete="RESTRICT"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    origin: Mapped[str] = mapped_column(String(64), nullable=False, default="extension")
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="started")
    final_result: Mapped[str | None] = mapped_column(String(32), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["Job | None"] = relationship(back_populates="application_sessions")
    profile_slot_ref: Mapped["ProfileSlot"] = relationship(back_populates="application_sessions")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ApplicationEvent.created_at",
    )


class ApplicationEvent(Base):
    __tablename__ = "application_events"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("application_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selector: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    detail_json: Mapped[dict | list | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["ApplicationSession"] = relationship(back_populates="events")
