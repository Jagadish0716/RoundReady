"""Create interviewer profiles, skills, availability, and outbox.

Revision ID: 0001_interviewer
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_interviewer"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    status = postgresql.ENUM(
        "pending", "under_review", "verified", "rejected", "suspended",
        name="verification_status", create_type=False,
    )
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "interviewer_profiles",
        sa.Column("user_id", sa.Uuid(), primary_key=True),
        sa.Column("headline", sa.String(180), nullable=False),
        sa.Column("company", sa.String(160)), sa.Column("job_title", sa.String(160)),
        sa.Column("experience_years", sa.Numeric(4, 1), server_default="0.0", nullable=False),
        sa.Column("linkedin_url", sa.String(2048)), sa.Column("github_url", sa.String(2048)),
        sa.Column("bio", sa.Text()),
        sa.Column("verification_status", status, server_default="pending", nullable=False),
        sa.Column("verification_reason", sa.Text()), sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("rating_average", sa.Numeric(3, 2), server_default="0.00", nullable=False),
        sa.Column("rating_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_interviews", sa.Integer(), server_default="0", nullable=False),
        sa.Column("reliability_score", sa.Numeric(5, 2), server_default="100.00", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("experience_years >= 0 AND experience_years <= 60", name="ck_interviewer_experience"),
        sa.CheckConstraint("rating_average >= 0 AND rating_average <= 5", name="ck_interviewer_rating"),
        sa.CheckConstraint("reliability_score >= 0 AND reliability_score <= 100", name="ck_interviewer_reliability"),
    )
    op.create_index("ix_interviewer_profiles_verification", "interviewer_profiles", ["verification_status", "created_at"])
    op.create_table(
        "interviewer_skills",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(64), nullable=False), sa.Column("topic", sa.String(120), nullable=False),
        sa.Column("skill_name", sa.String(120), nullable=False),
        sa.Column("experience_years", sa.Numeric(4, 1), server_default="0.0", nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["interviewer_profiles.user_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "domain", "topic", "skill_name", name="uq_interviewer_skill"),
        sa.CheckConstraint("experience_years >= 0 AND experience_years <= 60", name="ck_skill_experience"),
    )
    op.create_index("ix_interviewer_skills_user_id", "interviewer_skills", ["user_id"])
    op.create_index("ix_interviewer_skills_domain", "interviewer_skills", ["domain"])
    op.create_table(
        "weekly_availability_rules",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False), sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False), sa.Column("timezone", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["interviewer_profiles.user_id"], ondelete="CASCADE"),
        sa.CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_availability_weekday"),
        sa.CheckConstraint("start_time < end_time", name="ck_availability_time_range"),
        sa.UniqueConstraint("user_id", "weekday", "start_time", "end_time", "timezone", name="uq_weekly_availability"),
    )
    op.create_index("ix_weekly_availability_rules_user_id", "weekly_availability_rules", ["user_id"])
    op.create_table(
        "availability_blockouts",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["interviewer_profiles.user_id"], ondelete="CASCADE"),
        sa.CheckConstraint("starts_at < ends_at", name="ck_blockout_time_range"),
    )
    op.create_index("ix_availability_blockouts_user_time", "availability_blockouts", ["user_id", "starts_at", "ends_at"])
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("publish_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text()),
    )
    op.create_index("ix_interviewer_outbox_unpublished", "outbox_events", ["published_at", "occurred_at"])


def downgrade() -> None:
    op.drop_table("outbox_events")
    op.drop_table("availability_blockouts")
    op.drop_table("weekly_availability_rules")
    op.drop_table("interviewer_skills")
    op.drop_table("interviewer_profiles")
    postgresql.ENUM(name="verification_status").drop(op.get_bind(), checkfirst=True)
