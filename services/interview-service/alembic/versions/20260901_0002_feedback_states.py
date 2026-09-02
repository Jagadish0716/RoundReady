"""Add explicit manual-feedback lifecycle states."""

from collections.abc import Sequence

from alembic import op

revision: str = "20260901_0002"
down_revision: str | None = "20260827_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE interview_session_status ADD VALUE IF NOT EXISTS 'feedback_pending'")
    op.execute("ALTER TYPE interview_session_status ADD VALUE IF NOT EXISTS 'feedback_submitted'")


def downgrade() -> None:
    # PostgreSQL enum value removal requires a table/type rewrite and is intentionally non-destructive.
    pass
