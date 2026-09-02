"""Add user ownership and read state to notification deliveries."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260902_0002"
down_revision = "20260827_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("recipient_user_id", sa.Uuid(), nullable=True))
    op.add_column(
        "notifications", sa.Column("read_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(
        "ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_column("notifications", "read_at")
    op.drop_column("notifications", "recipient_user_id")
