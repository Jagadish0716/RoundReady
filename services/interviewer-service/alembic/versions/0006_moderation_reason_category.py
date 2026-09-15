"""Add controlled moderation reason category.

Revision ID: 0006_moderation_reason
Revises: 0005_interviewer_soft_delete
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_moderation_reason"
down_revision: str | None = "0005_interviewer_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interviewer_verification_review_history",
        sa.Column("reason_category", sa.String(length=96), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interviewer_verification_review_history", "reason_category")
