from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def enum_values(enum: type[StrEnum]) -> list[str]:
    return [item.value for item in enum]


class Base(DeclarativeBase):
    pass


class Channel(StrEnum):
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    RETRY_SCHEDULED = "retry_scheduled"
    SENT = "sent"
    DEAD_LETTERED = "dead_lettered"


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("event_id", "channel", "recipient", name="uq_notification_delivery"),
        Index("ix_notification_retry", "status", "next_attempt_at"),
        CheckConstraint("attempt_count >= 0", name="ck_notification_attempts"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    correlation_id: Mapped[str] = mapped_column(String(128), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    channel: Mapped[Channel] = mapped_column(
        Enum(Channel, name="notification_channel", values_callable=enum_values)
    )
    template: Mapped[str] = mapped_column(String(128))
    template_version: Mapped[int] = mapped_column(Integer, default=1)
    rendered_subject: Mapped[str | None] = mapped_column(String(255))
    rendered_body: Mapped[str] = mapped_column(Text)
    status: Mapped[DeliveryStatus] = mapped_column(
        Enum(DeliveryStatus, name="delivery_status", values_callable=enum_values),
        default=DeliveryStatus.PENDING,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DeliveryAttempt(Base):
    __tablename__ = "delivery_attempts"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    notification_id: Mapped[UUID] = mapped_column(
        ForeignKey("notifications.id", ondelete="CASCADE"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    successful: Mapped[bool]
    provider_reference: Mapped[str | None] = mapped_column(String(255))
    error_code: Mapped[str | None] = mapped_column(String(128))


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class DeadLetterRecord(Base):
    __tablename__ = "dead_letter_records"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID | None] = mapped_column(index=True)
    notification_id: Mapped[UUID | None] = mapped_column(ForeignKey("notifications.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(128))
    correlation_id: Mapped[str] = mapped_column(String(128))
    reason_code: Mapped[str] = mapped_column(String(128))
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
