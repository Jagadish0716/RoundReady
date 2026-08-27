"""Payment persistence, webhook inbox, audit history, and outbox."""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260826_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

payment_status = postgresql.ENUM("created", "pending", "authorized", "captured", "failed", "refund_pending", "refunded", "partially_refunded", name="payment_status", create_type=False)
refund_status = postgresql.ENUM("pending", "processed", "failed", name="refund_status", create_type=False)
webhook_status = postgresql.ENUM("received", "processed", "ignored", "failed", name="webhook_processing_status", create_type=False)

def upgrade() -> None:
    payment_status.create(op.get_bind())
    refund_status.create(op.get_bind())
    webhook_status.create(op.get_bind())
    op.create_table("payments",
        sa.Column("id", sa.Uuid(), nullable=False), sa.Column("booking_id", sa.Uuid(), nullable=False), sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("currency", sa.String(3), nullable=False), sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_order_id", sa.String(255)), sa.Column("provider_payment_id", sa.String(255)), sa.Column("status", payment_status, nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_paise = 20000", name="ck_payment_price"), sa.CheckConstraint("currency = 'INR'", name="ck_payment_currency"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("booking_id"), sa.UniqueConstraint("provider_order_id"), sa.UniqueConstraint("provider_payment_id"), sa.UniqueConstraint("candidate_id", "idempotency_key", name="uq_payment_idempotency"))
    op.create_index("ix_payments_booking_id", "payments", ["booking_id"]); op.create_index("ix_payments_candidate_id", "payments", ["candidate_id"])
    op.create_table("refunds", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id"), nullable=False), sa.Column("provider_refund_id", sa.String(255), unique=True), sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("reason", sa.String(500), nullable=False), sa.Column("status", refund_status, nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.CheckConstraint("amount_paise > 0", name="ck_refund_positive"))
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_table("webhook_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("provider", sa.String(32), nullable=False), sa.Column("provider_event_id", sa.String(255), nullable=False), sa.Column("event_type", sa.String(128), nullable=False), sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("received_at", sa.DateTime(timezone=True), nullable=False), sa.Column("processed_at", sa.DateTime(timezone=True)), sa.Column("processing_status", webhook_status, nullable=False), sa.Column("last_error", sa.String(255)), sa.UniqueConstraint("provider", "provider_event_id", name="uq_webhook_provider_event"))
    op.create_index("ix_webhook_processing", "webhook_events", ["processing_status", "received_at"])
    op.create_table("payment_transactions", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("payments.id"), nullable=False), sa.Column("action", sa.String(64), nullable=False), sa.Column("from_status", payment_status), sa.Column("to_status", payment_status, nullable=False), sa.Column("amount_paise", sa.Integer(), nullable=False), sa.Column("provider_reference", sa.String(255)), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_payment_transactions_payment_id", "payment_transactions", ["payment_id"])
    op.create_table("outbox_events", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("event_type", sa.String(128), nullable=False), sa.Column("event_version", sa.Integer(), nullable=False), sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False), sa.Column("correlation_id", sa.String(128), nullable=False), sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("publish_attempts", sa.Integer(), nullable=False), sa.Column("last_error", sa.Text()))
    op.create_index("ix_outbox_events_published_at", "outbox_events", ["published_at"])

def downgrade() -> None:
    for table in ("outbox_events", "payment_transactions", "webhook_events", "refunds", "payments"):
        op.drop_table(table)
    webhook_status.drop(op.get_bind()); refund_status.drop(op.get_bind()); payment_status.drop(op.get_bind())
