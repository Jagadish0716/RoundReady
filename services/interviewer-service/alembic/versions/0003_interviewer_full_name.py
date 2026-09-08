"""Add interviewer full name.

Revision ID: 0003_interviewer_full_name
Revises: 0002_layered_verification
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_interviewer_full_name"
down_revision: str | None = "0002_layered_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interviewer_profiles",
        sa.Column("full_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("interviewer_profiles", "full_name")
