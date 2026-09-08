"""Add secure interviewer contact verification.

Revision ID: 0004_contact_verification
Revises: 0003_interviewer_full_name
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_contact_verification"
down_revision: str | None = "0003_interviewer_full_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviewer_contact_verifications",
        sa.Column("interviewer_id", sa.Uuid(), nullable=False),
        sa.Column("mobile_e164", sa.String(32), nullable=True),
        sa.Column("mobile_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("company_email", sa.String(320), nullable=True),
        sa.Column("company_email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["interviewer_id"], ["interviewer_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("interviewer_id"),
    )
    op.create_table(
        "contact_verification_challenges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("interviewer_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("target_fingerprint", sa.String(64), nullable=False),
        sa.Column("secret_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resend_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["interviewer_id"], ["interviewer_profiles.user_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_contact_verification_challenges_interviewer_id",
        "contact_verification_challenges",
        ["interviewer_id"],
    )
    op.create_index(
        "ix_contact_challenge_owner_kind",
        "contact_verification_challenges",
        ["interviewer_id", "kind", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_contact_challenge_owner_kind", table_name="contact_verification_challenges")
    op.drop_index(
        "ix_contact_verification_challenges_interviewer_id",
        table_name="contact_verification_challenges",
    )
    op.drop_table("contact_verification_challenges")
    op.drop_table("interviewer_contact_verifications")
