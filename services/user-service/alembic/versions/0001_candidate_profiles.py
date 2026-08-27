"""Create candidate profile and resume metadata tables.

Revision ID: 0001_candidate_profiles
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_candidate_profiles"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "candidate_profiles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("phone", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column(
            "experience_years",
            sa.Numeric(precision=4, scale=1),
            server_default="0.0",
            nullable=False,
        ),
        sa.Column("current_role", sa.String(length=160), nullable=True),
        sa.Column("target_role", sa.String(length=160), nullable=True),
        sa.Column(
            "preferred_language", sa.String(length=64), server_default="English", nullable=False
        ),
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
        sa.Column("resume_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "experience_years >= 0 AND experience_years <= 60",
            name="ck_candidate_profiles_experience_years",
        ),
        sa.CheckConstraint(
            "phone IS NULL OR phone ~ '^\\+[1-9][0-9]{7,14}$'",
            name="ck_candidate_profiles_phone_e164",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_candidate_profiles_city", "candidate_profiles", ["city"])
    op.create_index(
        "ix_candidate_profiles_target_role", "candidate_profiles", ["target_role"]
    )
    op.create_table(
        "resume_metadata",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("storage_url", sa.String(length=2048), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("size_bytes > 0", name="ck_resume_metadata_positive_size"),
        sa.CheckConstraint(
            "checksum_sha256 ~ '^[a-f0-9]{64}$'", name="ck_resume_metadata_sha256"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["candidate_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("resume_metadata")
    op.drop_index("ix_candidate_profiles_target_role", table_name="candidate_profiles")
    op.drop_index("ix_candidate_profiles_city", table_name="candidate_profiles")
    op.drop_table("candidate_profiles")
