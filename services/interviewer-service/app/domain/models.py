from datetime import UTC, datetime, time
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class VerificationStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class InterviewerProfile(Base):
    __tablename__ = "interviewer_profiles"
    __table_args__ = (
        CheckConstraint(
            "experience_years >= 0 AND experience_years <= 60", name="ck_interviewer_experience"
        ),
        CheckConstraint(
            "rating_average >= 0 AND rating_average <= 5", name="ck_interviewer_rating"
        ),
        CheckConstraint(
            "reliability_score >= 0 AND reliability_score <= 100", name="ck_interviewer_reliability"
        ),
        Index("ix_interviewer_profiles_verification", "verification_status", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    headline: Mapped[str] = mapped_column(String(180))
    company: Mapped[str | None] = mapped_column(String(160), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    experience_years: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("0.0"))
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(
            VerificationStatus,
            name="verification_status",
            values_callable=lambda statuses: [item.value for item in statuses],
        ),
        default=VerificationStatus.PENDING,
    )
    verification_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rating_average: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    rating_count: Mapped[int] = mapped_column(default=0)
    completed_interviews: Mapped[int] = mapped_column(default=0)
    reliability_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("100.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class InterviewerSkill(Base):
    __tablename__ = "interviewer_skills"
    __table_args__ = (
        UniqueConstraint("user_id", "domain", "topic", "skill_name", name="uq_interviewer_skill"),
        CheckConstraint(
            "experience_years >= 0 AND experience_years <= 60", name="ck_skill_experience"
        ),
        Index("ix_interviewer_skills_domain", "domain"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    domain: Mapped[str] = mapped_column(String(64))
    topic: Mapped[str] = mapped_column(String(120))
    skill_name: Mapped[str] = mapped_column(String(120))
    experience_years: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("0.0"))


class WeeklyAvailabilityRule(Base):
    __tablename__ = "weekly_availability_rules"
    __table_args__ = (
        CheckConstraint("weekday >= 0 AND weekday <= 6", name="ck_availability_weekday"),
        CheckConstraint("start_time < end_time", name="ck_availability_time_range"),
        UniqueConstraint(
            "user_id",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            name="uq_weekly_availability",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int]
    start_time: Mapped[time] = mapped_column(Time(timezone=False))
    end_time: Mapped[time] = mapped_column(Time(timezone=False))
    timezone: Mapped[str] = mapped_column(String(64))


class AvailabilityBlockout(Base):
    __tablename__ = "availability_blockouts"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_blockout_time_range"),
        Index("ix_availability_blockouts_user_time", "user_id", "starts_at", "ends_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_interviewer_outbox_unpublished", "published_at", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_type: Mapped[str] = mapped_column(String(128))
    event_version: Mapped[int]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    correlation_id: Mapped[str] = mapped_column(String(128))
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    publish_attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
