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


class VerificationCheckType(StrEnum):
    EMAIL_VERIFIED = "email_verified"
    MOBILE_VERIFIED = "mobile_verified"
    LINKEDIN_REVIEWED = "linkedin_reviewed"
    COMPANY_EMAIL_VERIFIED = "company_email_verified"
    PROFESSIONAL_EVIDENCE_REVIEWED = "professional_evidence_reviewed"
    SCREENING_CALL_PASSED = "screening_call_passed"


class EvidenceType(StrEnum):
    LINKEDIN = "linkedin"
    COMPANY_EMAIL = "company_email"
    GITHUB_OR_PORTFOLIO = "github_or_portfolio"
    SUPPORTING_DOCUMENT = "supporting_document"


class EvidenceStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class ScreeningStatus(StrEnum):
    NOT_SCHEDULED = "not_scheduled"
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


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
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_admin_id: Mapped[UUID | None] = mapped_column(nullable=True)
    deletion_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class InterviewerVerification(Base):
    __tablename__ = "interviewer_verifications"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default=VerificationStatus.PENDING.value)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VerificationEvidence(Base):
    __tablename__ = "interviewer_verification_evidence"
    __table_args__ = (
        UniqueConstraint("interviewer_id", "evidence_type", name="uq_verification_evidence_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(48))
    value_reference: Mapped[str] = mapped_column(String(2048))
    status: Mapped[str] = mapped_column(String(32), default=EvidenceStatus.PENDING.value)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)


class VerificationCheck(Base):
    __tablename__ = "interviewer_verification_checks"
    __table_args__ = (
        UniqueConstraint("interviewer_id", "check_type", name="uq_verification_check_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    check_type: Mapped[str] = mapped_column(String(64))
    passed: Mapped[bool] = mapped_column(default=False)
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScreeningCall(Base):
    __tablename__ = "interviewer_screening_calls"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), unique=True, index=True
    )
    screening_status: Mapped[str] = mapped_column(
        String(32), default=ScreeningStatus.NOT_SCHEDULED.value
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    communication_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_result: Mapped[str | None] = mapped_column(String(32), nullable=True)


class VerificationReviewHistory(Base):
    __tablename__ = "interviewer_verification_review_history"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(48))
    from_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32))
    reviewed_by: Mapped[UUID] = mapped_column()
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class InterviewerContactVerification(Base):
    __tablename__ = "interviewer_contact_verifications"

    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    mobile_e164: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mobile_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    company_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    company_email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ContactVerificationChallenge(Base):
    __tablename__ = "contact_verification_challenges"
    __table_args__ = (
        Index("ix_contact_challenge_owner_kind", "interviewer_id", "kind", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    interviewer_id: Mapped[UUID] = mapped_column(
        ForeignKey("interviewer_profiles.user_id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    target_fingerprint: Mapped[str] = mapped_column(String(64))
    secret_hash: Mapped[str] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resend_available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
