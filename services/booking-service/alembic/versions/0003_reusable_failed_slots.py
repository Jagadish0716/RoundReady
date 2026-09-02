"""Allow a released slot to receive a replacement booking."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_reusable_failed_slots"
down_revision: str | None = "0002_interview_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_booking_slot", "bookings", type_="unique")
    op.create_index(
        "uq_booking_active_slot",
        "bookings",
        ["slot_id"],
        unique=True,
        postgresql_where=sa.text("occupies_time"),
    )


def downgrade() -> None:
    op.drop_index("uq_booking_active_slot", table_name="bookings")
    op.create_unique_constraint("uq_booking_slot", "bookings", ["slot_id"])
