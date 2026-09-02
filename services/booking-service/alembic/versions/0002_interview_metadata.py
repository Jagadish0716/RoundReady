"""Add interview contract metadata to slots and bookings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_interview_metadata"
down_revision: str | None = "0001_booking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ("slots", "bookings"):
        op.add_column(table, sa.Column("rubric_id", sa.Uuid(), nullable=True))
        op.add_column(table, sa.Column("domain", sa.String(80), nullable=True))
        op.add_column(table, sa.Column("topic", sa.String(120), nullable=True))
        op.add_column(table, sa.Column("experience_level", sa.String(40), nullable=True))
def downgrade() -> None:
    for table in ("bookings", "slots"):
        for column in ("experience_level", "topic", "domain", "rubric_id"):
            op.drop_column(table, column)
