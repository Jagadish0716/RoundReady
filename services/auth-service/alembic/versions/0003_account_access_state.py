"""Add authoritative account access projection.

Revision ID: 0003_account_access
Revises: 0002_email_verification
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_account_access"
down_revision: str | None = "0002_email_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "credentials",
        sa.Column("access_status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.add_column(
        "credentials", sa.Column("access_reason_category", sa.String(length=96), nullable=True)
    )
    op.add_column(
        "credentials", sa.Column("lifecycle_updated_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("credentials", sa.Column("lifecycle_event_id", sa.Uuid(), nullable=True))
    op.create_check_constraint(
        "ck_credentials_access_status",
        "credentials",
        "access_status IN ('active', 'blocked', 'disabled')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_credentials_access_status", "credentials", type_="check")
    op.drop_column("credentials", "lifecycle_event_id")
    op.drop_column("credentials", "lifecycle_updated_at")
    op.drop_column("credentials", "access_reason_category")
    op.drop_column("credentials", "access_status")
