from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"
    __table_args__ = (
        CheckConstraint(
            "experience_years >= 0 AND experience_years <= 60",
            name="ck_candidate_profiles_experience_years",
        ),
        CheckConstraint(
            "phone IS NULL OR phone ~ '^\\+[1-9][0-9]{7,14}$'",
            name="ck_candidate_profiles_phone_e164",
        ),
        Index("ix_candidate_profiles_city", "city"),
        Index("ix_candidate_profiles_target_role", "target_role"),
    )

    user_id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(16), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    experience_years: Mapped[Decimal] = mapped_column(Numeric(4, 1), default=Decimal("0.0"))
    current_role: Mapped[str | None] = mapped_column(String(160), nullable=True)
    target_role: Mapped[str | None] = mapped_column(String(160), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(64), default="English")
    linkedin_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    resume_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class ResumeMetadata(Base):
    __tablename__ = "resume_metadata"
    __table_args__ = (
        CheckConstraint("size_bytes > 0", name="ck_resume_metadata_positive_size"),
        CheckConstraint("checksum_sha256 ~ '^[a-f0-9]{64}$'", name="ck_resume_metadata_sha256"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    storage_url: Mapped[str] = mapped_column(String(2048))
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    checksum_sha256: Mapped[str] = mapped_column(String(64))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
