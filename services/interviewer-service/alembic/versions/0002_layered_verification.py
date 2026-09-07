"""add layered interviewer verification

Revision ID: 0002_layered_verification
Revises: 0001_interviewer
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_layered_verification"
down_revision: str | None = "0001_interviewer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interviewer_verifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interviewer_id",
            sa.Uuid(),
            sa.ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("suspension_reason", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_interviewer_verifications_interviewer_id",
        "interviewer_verifications",
        ["interviewer_id"],
    )
    op.create_table(
        "interviewer_verification_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interviewer_id",
            sa.Uuid(),
            sa.ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evidence_type", sa.String(48), nullable=False),
        sa.Column("value_reference", sa.String(2048), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.UniqueConstraint(
            "interviewer_id", "evidence_type", name="uq_verification_evidence_type"
        ),
    )
    op.create_index(
        "ix_verification_evidence_interviewer",
        "interviewer_verification_evidence",
        ["interviewer_id"],
    )
    op.create_table(
        "interviewer_verification_checks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interviewer_id",
            sa.Uuid(),
            sa.ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("check_type", sa.String(64), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("interviewer_id", "check_type", name="uq_verification_check_type"),
    )
    op.create_index(
        "ix_verification_checks_interviewer", "interviewer_verification_checks", ["interviewer_id"]
    )
    op.create_table(
        "interviewer_screening_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interviewer_id",
            sa.Uuid(),
            sa.ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "screening_status", sa.String(32), nullable=False, server_default="not_scheduled"
        ),
        sa.Column("reviewed_by", sa.Uuid()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("reviewer_notes", sa.Text()),
        sa.Column("communication_assessment", sa.Text()),
        sa.Column("technical_assessment", sa.Text()),
        sa.Column("overall_result", sa.String(32)),
    )
    op.create_index(
        "ix_screening_calls_interviewer", "interviewer_screening_calls", ["interviewer_id"]
    )
    op.create_table(
        "interviewer_verification_review_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "interviewer_id",
            sa.Uuid(),
            sa.ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(48), nullable=False),
        sa.Column("from_status", sa.String(32)),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_verification_history_interviewer",
        "interviewer_verification_review_history",
        ["interviewer_id"],
    )
    op.execute(
        "INSERT INTO interviewer_verifications (id, interviewer_id, status, submitted_at, reviewed_at, reviewed_by, rejection_reason, suspension_reason) SELECT gen_random_uuid(), user_id, verification_status::text, CASE WHEN verification_status::text <> 'pending' THEN updated_at END, reviewed_at, reviewed_by, CASE WHEN verification_status::text = 'rejected' THEN verification_reason END, CASE WHEN verification_status::text = 'suspended' THEN verification_reason END FROM interviewer_profiles"
    )
    op.execute(
        "INSERT INTO outbox_events (id, event_type, event_version, correlation_id, payload) SELECT gen_random_uuid(), 'interviewer.verification.approved.v1', 1, 'migration:0002_layered_verification', jsonb_build_object('interviewer_id', user_id::text) FROM interviewer_profiles WHERE verification_status::text = 'verified'"
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM outbox_events WHERE correlation_id = 'migration:0002_layered_verification'"
    )
    op.drop_table("interviewer_verification_review_history")
    op.drop_table("interviewer_screening_calls")
    op.drop_table("interviewer_verification_checks")
    op.drop_table("interviewer_verification_evidence")
    op.drop_table("interviewer_verifications")
