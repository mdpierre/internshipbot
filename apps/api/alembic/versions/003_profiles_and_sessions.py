"""add profile slots and application sessions

Revision ID: 003
Revises: 002
Create Date: 2026-03-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "profile_slots",
        sa.Column("slot", sa.String(length=32), primary_key=True),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("profile_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("first_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("last_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("full_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("email", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("phone", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("city", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("state", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("zip", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("country", sa.String(length=255), nullable=False, server_default="United States"),
        sa.Column("linkedin", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("website", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("github", sa.String(length=2048), nullable=False, server_default=""),
        sa.Column("target_title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("target_salary", sa.String(length=255), nullable=False, server_default=""),
        sa.Column(
            "work_authorization",
            sa.String(length=255),
            nullable=False,
            server_default="Yes - U.S. Citizen or Permanent Resident",
        ),
        sa.Column("require_sponsorship", sa.String(length=64), nullable=False, server_default="No"),
        sa.Column("veteran", sa.String(length=64), nullable=False, server_default="No"),
        sa.Column("disability", sa.String(length=64), nullable=False, server_default="Prefer not to say"),
        sa.Column("gender", sa.String(length=64), nullable=False, server_default="Prefer not to say"),
        sa.Column("ethnicity", sa.String(length=128), nullable=False, server_default="Prefer not to say"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("resume_label", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("resume_filename", sa.String(length=255), nullable=True),
        sa.Column("resume_path", sa.String(length=2048), nullable=True),
        sa.Column("resume_content_type", sa.String(length=255), nullable=True),
        sa.Column("resume_uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "profile_experiences",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_slot_id", sa.String(length=32), sa.ForeignKey("profile_slots.slot", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("employer", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("title", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("start_date", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("end_date", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("location", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.UniqueConstraint("profile_slot_id", "sort_order", name="uq_profile_experience_order"),
    )

    op.create_table(
        "profile_educations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_slot_id", sa.String(length=32), sa.ForeignKey("profile_slots.slot", ondelete="CASCADE"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("school", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("degree", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("major", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("graduation_year", sa.String(length=16), nullable=False, server_default=""),
        sa.Column("gpa", sa.String(length=32), nullable=False, server_default=""),
        sa.UniqueConstraint("profile_slot_id", "sort_order", name="uq_profile_education_order"),
    )

    op.create_table(
        "application_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("profile_slot", sa.String(length=32), sa.ForeignKey("profile_slots.slot", ondelete="RESTRICT"), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("page_url", sa.String(length=2048), nullable=False),
        sa.Column("origin", sa.String(length=64), nullable=False, server_default="extension"),
        sa.Column("state", sa.String(length=32), nullable=False, server_default="started"),
        sa.Column("final_result", sa.String(length=32), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "application_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("application_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("field_name", sa.String(length=128), nullable=True),
        sa.Column("selector", sa.String(length=1024), nullable=True),
        sa.Column("detail_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    op.bulk_insert(
        sa.table(
            "profile_slots",
            sa.column("slot", sa.String),
            sa.column("display_name", sa.String),
            sa.column("profile_name", sa.String),
            sa.column("is_active", sa.Boolean),
        ),
        [
            {"slot": "profile_1", "display_name": "Profile 1", "profile_name": "Profile 1", "is_active": True},
            {"slot": "profile_2", "display_name": "Profile 2", "profile_name": "Profile 2", "is_active": False},
            {"slot": "profile_3", "display_name": "Profile 3", "profile_name": "Profile 3", "is_active": False},
        ],
    )


def downgrade() -> None:
    op.drop_table("application_events")
    op.drop_table("application_sessions")
    op.drop_table("profile_educations")
    op.drop_table("profile_experiences")
    op.drop_table("profile_slots")
