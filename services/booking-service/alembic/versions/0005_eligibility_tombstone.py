"""Preserve irreversible deletion in the eligibility projection."""
from alembic import op
import sqlalchemy as sa
revision = "0005_eligibility_tombstone"
down_revision = "0004_interviewer_eligibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("interviewer_eligibility", sa.Column(
        "deleted", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("interviewer_eligibility", "deleted")
