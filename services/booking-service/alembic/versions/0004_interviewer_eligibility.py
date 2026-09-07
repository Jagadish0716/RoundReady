"""add interviewer booking eligibility

Revision ID: 0004_interviewer_eligibility
Revises: 0003_reusable_failed_slots
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_interviewer_eligibility"
down_revision: str | None = "0003_reusable_failed_slots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviewer_eligibility",
        sa.Column("interviewer_id", sa.Uuid(), primary_key=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )


def downgrade() -> None:
    op.drop_table("interviewer_eligibility")
