from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
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
from sqlalchemy.dialects.postgresql import TSTZRANGE, ExcludeConstraint, Range
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class SlotStatus(StrEnum):
    AVAILABLE = "available"
    HELD = "held"
    BOOKED = "booked"
    BLOCKED = "blocked"


class BookingStatus(StrEnum):
    PAYMENT_PENDING = "payment_pending"
    BOOKED = "booked"
    CONFIRMED = "confirmed"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FEEDBACK_PENDING = "feedback_pending"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    SETTLED = "settled"
    CANCELLED = "cancelled"
    PAYMENT_FAILED = "payment_failed"
    CANDIDATE_NO_SHOW = "candidate_no_show"
    INTERVIEWER_NO_SHOW = "interviewer_no_show"
    TECHNICAL_FAILURE = "technical_failure"
    REFUNDED = "refunded"
    RESCHEDULED = "rescheduled"


def enum_values(enum: type[StrEnum]) -> list[str]:
    return [item.value for item in enum]


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_slots_time_range"),
        UniqueConstraint("interviewer_id", "starts_at", "ends_at", name="uq_interviewer_slot"),
        Index("ix_slots_availability", "status", "starts_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, name="slot_status", values_callable=enum_values),
        default=SlotStatus.AVAILABLE,
    )
    held_by_candidate_id: Mapped[UUID | None] = mapped_column(nullable=True)
    hold_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hold_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        ExcludeConstraint(
            ("candidate_id", "="),
            ("time_range", "&&"),
            where="occupies_time",
            using="gist",
            name="ex_bookings_candidate_overlap",
        ),
        ExcludeConstraint(
            ("interviewer_id", "="),
            ("time_range", "&&"),
            where="occupies_time",
            using="gist",
            name="ex_bookings_interviewer_overlap",
        ),
        UniqueConstraint("candidate_id", "idempotency_key", name="uq_booking_idempotency"),
        UniqueConstraint("slot_id", name="uq_booking_slot"),
        CheckConstraint("amount_paise = 20000", name="ck_booking_price"),
        CheckConstraint("currency = 'INR'", name="ck_booking_currency"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slot_id: Mapped[UUID] = mapped_column(ForeignKey("slots.id"), index=True)
    candidate_id: Mapped[UUID] = mapped_column(index=True)
    interviewer_id: Mapped[UUID] = mapped_column(index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    time_range: Mapped[Range[datetime]] = mapped_column(TSTZRANGE, nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", values_callable=enum_values)
    )
    occupies_time: Mapped[bool] = mapped_column(Boolean, default=True)
    amount_paise: Mapped[int] = mapped_column(Integer, default=20000)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    idempotency_key: Mapped[str] = mapped_column(String(128))
    payment_id: Mapped[UUID | None] = mapped_column(nullable=True)
    rescheduled_from_id: Mapped[UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    from_status: Mapped[BookingStatus | None] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            values_callable=enum_values,
            create_constraint=False,
        ),
        nullable=True,
    )
    to_status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            name="booking_status",
            values_callable=enum_values,
            create_constraint=False,
        )
    )
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128))
    event_version: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    correlation_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    publish_attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
