"""Add interviewer soft deletion metadata.

Revision ID: 0005_interviewer_soft_delete
Revises: 0004_contact_verification
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0005_interviewer_soft_delete"
down_revision: str | None = "0004_contact_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    op.add_column("interviewer_profiles", sa.Column("deleted_at", sa.DateTime(timezone=True)))
    op.add_column("interviewer_profiles", sa.Column("deleted_by_admin_id", sa.Uuid()))
    op.add_column("interviewer_profiles", sa.Column("deletion_reason", sa.Text()))
    op.create_index("ix_interviewer_profiles_deleted_at", "interviewer_profiles", ["deleted_at"])

def downgrade() -> None:
    op.drop_index("ix_interviewer_profiles_deleted_at", table_name="interviewer_profiles")
    op.drop_column("interviewer_profiles", "deletion_reason")
    op.drop_column("interviewer_profiles", "deleted_by_admin_id")
    op.drop_column("interviewer_profiles", "deleted_at")
