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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


def enum_values(enum: type[StrEnum]) -> list[str]:
    return [item.value for item in enum]


class Base(DeclarativeBase):
    pass


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANDIDATE_NO_SHOW = "candidate_no_show"
    INTERVIEWER_NO_SHOW = "interviewer_no_show"
    TECHNICAL_FAILURE = "technical_failure"
    CANCELLED = "cancelled"


class ParticipantRole(StrEnum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"


class ReadinessLevel(StrEnum):
    NOT_READY = "not_ready"
    DEVELOPING = "developing"
    INTERVIEW_READY = "interview_ready"
    STRONG = "strong"


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        CheckConstraint("scheduled_start < scheduled_end", name="ck_interview_schedule"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    booking_id: Mapped[UUID] = mapped_column(unique=True, index=True)
    candidate_id: Mapped[UUID] = mapped_column(index=True)
    interviewer_id: Mapped[UUID] = mapped_column(index=True)
    rubric_id: Mapped[UUID] = mapped_column(ForeignKey("rubrics.id"))
    room_reference: Mapped[str | None] = mapped_column(String(255), unique=True)
    scheduled_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    scheduled_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="interview_session_status", values_callable=enum_values),
        default=SessionStatus.SCHEDULED,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ParticipantAttendance(Base):
    __tablename__ = "participant_attendance"
    __table_args__ = (UniqueConstraint("session_id", "role", name="uq_attendance_session_role"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(index=True)
    role: Mapped[ParticipantRole] = mapped_column(
        Enum(ParticipantRole, name="participant_role", values_callable=enum_values)
    )
    first_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected: Mapped[bool] = mapped_column(Boolean, default=False)
    reconnect_count: Mapped[int] = mapped_column(Integer, default=0)
    total_connected_seconds: Mapped[int] = mapped_column(Integer, default=0)


class Rubric(Base):
    __tablename__ = "rubrics"
    __table_args__ = (
        UniqueConstraint(
            "domain", "topic", "experience_level", "version", name="uq_rubric_version"
        ),
        CheckConstraint("maximum_score > 0", name="ck_rubric_max_score"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    domain: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str] = mapped_column(String(120))
    experience_level: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer)
    criteria: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    maximum_score: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FeedbackReport(Base):
    __tablename__ = "feedback_reports"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("interview_sessions.id"), unique=True, index=True
    )
    interviewer_id: Mapped[UUID] = mapped_column(index=True)
    criterion_scores: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    strengths: Mapped[list[str]] = mapped_column(JSON)
    improvement_areas: Mapped[list[str]] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(String(4000))
    readiness_level: Mapped[ReadinessLevel] = mapped_column(
        Enum(ReadinessLevel, name="readiness_level", values_callable=enum_values)
    )
    total_score: Mapped[int] = mapped_column(Integer)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ProcessedEvent(Base):
    __tablename__ = "processed_events"
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128))
    event_version: Mapped[int] = mapped_column(default=1)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    correlation_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    publish_attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text)


class AttendanceEvent(Base):
    __tablename__ = "attendance_events"
    __table_args__ = (Index("ix_attendance_events_session_occurred", "session_id", "occurred_at"),)
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    provider_event_id: Mapped[str] = mapped_column(String(255), unique=True)
    session_id: Mapped[UUID] = mapped_column(ForeignKey("interview_sessions.id"))
    participant_id: Mapped[UUID] = mapped_column(ForeignKey("participant_attendance.id"))
    event_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
