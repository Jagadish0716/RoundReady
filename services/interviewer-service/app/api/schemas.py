from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.models import (
    EvidenceStatus,
    EvidenceType,
    ScreeningStatus,
    VerificationCheckType,
    VerificationStatus,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
    model_validator,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Domain(StrEnum):
    DEVOPS = "DevOps"
    AWS = "AWS"
    AZURE = "Azure"
    BACKEND = "Backend"
    FULL_STACK = "Full Stack"
    QA = "QA"
    TECH_SUPPORT = "Tech Support"


class ProfileUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[NonBlank, Field(min_length=2, max_length=100)]
    headline: Annotated[NonBlank, Field(max_length=180)]
    company: Annotated[NonBlank, Field(max_length=160)]
    job_title: Annotated[NonBlank, Field(max_length=160)]
    experience_years: Decimal = Field(ge=0, le=60, decimal_places=1)
    linkedin_url: HttpUrl
    github_url: HttpUrl
    bio: Annotated[NonBlank, Field(min_length=50, max_length=4000)]

    @field_validator("linkedin_url")
    @classmethod
    def linkedin_host(cls, value: HttpUrl) -> HttpUrl:
        host = value.host or ""
        path = (value.path or "").rstrip("/")
        if (
            (host != "linkedin.com" and not host.endswith(".linkedin.com"))
            or not path.startswith("/in/")
            or len(path.removeprefix("/in/")) == 0
        ):
            raise ValueError("linkedin_url must be a LinkedIn /in/ profile URL")
        return value

    @field_validator("github_url")
    @classmethod
    def github_host(cls, value: HttpUrl) -> HttpUrl:
        segments = [segment for segment in (value.path or "").split("/") if segment]
        if value.host not in {"github.com", "www.github.com"} or len(segments) != 1:
            raise ValueError("github_url must be a GitHub profile URL")
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    full_name: str | None
    headline: str
    company: str | None
    job_title: str | None
    experience_years: Decimal
    linkedin_url: str | None
    github_url: str | None
    bio: str | None
    verification_status: VerificationStatus
    verification_reason: str | None
    rating_average: Decimal
    rating_count: int
    completed_interviews: int
    reliability_score: Decimal
    deleted_at: datetime | None = None
    deleted_by_admin_id: UUID | None = None
    deletion_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class SkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    domain: Domain
    topic: Annotated[NonBlank, Field(max_length=120)]
    skill_name: Annotated[NonBlank, Field(max_length=120)]
    experience_years: Decimal = Field(default=Decimal("0.0"), ge=0, le=60, decimal_places=1)


class SkillReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skills: list[SkillItem] = Field(max_length=50)

    @field_validator("skills")
    @classmethod
    def unique_skills(cls, value: list[SkillItem]) -> list[SkillItem]:
        keys = {(item.domain, item.topic.casefold(), item.skill_name.casefold()) for item in value}
        if len(keys) != len(value):
            raise ValueError("skills must be unique")
        return value


class SkillResponse(SkillItem):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class WeeklyRuleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    timezone: Annotated[NonBlank, Field(max_length=64)]

    @model_validator(mode="after")
    def valid_rule(self) -> "WeeklyRuleInput":
        if self.start_time >= self.end_time:
            raise ValueError("start_time must be before end_time")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return self


class WeeklyRulesReplaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rules: list[WeeklyRuleInput] = Field(max_length=50)

    @field_validator("rules")
    @classmethod
    def non_overlapping(cls, rules: list[WeeklyRuleInput]) -> list[WeeklyRuleInput]:
        grouped: dict[tuple[int, str], list[WeeklyRuleInput]] = {}
        for rule in rules:
            grouped.setdefault((rule.weekday, rule.timezone), []).append(rule)
        for group in grouped.values():
            ordered = sorted(group, key=lambda rule: rule.start_time)
            if any(
                left.end_time > right.start_time
                for left, right in zip(ordered, ordered[1:], strict=False)
            ):
                raise ValueError("weekly availability rules cannot overlap")
        return rules


class WeeklyRuleResponse(WeeklyRuleInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class BlockoutCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    starts_at: datetime
    ends_at: datetime
    reason: Annotated[NonBlank, Field(max_length=255)] | None = None

    @model_validator(mode="after")
    def valid_blockout(self) -> "BlockoutCreateRequest":
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("blockout timestamps must include a timezone")
        if self.starts_at >= self.ends_at:
            raise ValueError("starts_at must be before ends_at")
        return self


class BlockoutResponse(BlockoutCreateRequest):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class RejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Annotated[NonBlank, Field(max_length=1000)]


class SuspensionRequest(RejectionRequest):
    pass


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_type: EvidenceType
    value_reference: Annotated[NonBlank, Field(max_length=2048)]

    @model_validator(mode="after")
    def safe_reference(self) -> "EvidenceInput":
        if self.evidence_type is EvidenceType.SUPPORTING_DOCUMENT:
            if not self.value_reference.startswith("private-object://"):
                raise ValueError("supporting documents require a private object reference")
        elif self.evidence_type is EvidenceType.COMPANY_EMAIL:
            if "@" not in self.value_reference or len(self.value_reference) > 320:
                raise ValueError("company email is invalid")
        else:
            parsed = HttpUrl(self.value_reference)
            if self.evidence_type is EvidenceType.LINKEDIN:
                host = parsed.host or ""
                if host != "linkedin.com" and not host.endswith(".linkedin.com"):
                    raise ValueError("LinkedIn evidence must use linkedin.com")
        return self


class EvidenceResponse(EvidenceInput):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: EvidenceStatus
    reviewer_notes: str | None
    created_at: datetime
    reviewed_at: datetime | None


class VerificationCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    check_type: VerificationCheckType
    passed: bool
    reviewed_at: datetime | None


class ScreeningInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    screening_status: ScreeningStatus
    reviewer_notes: Annotated[str, Field(max_length=2000)] | None = None
    communication_assessment: Annotated[str, Field(max_length=2000)] | None = None
    technical_assessment: Annotated[str, Field(max_length=2000)] | None = None
    overall_result: Annotated[str, Field(max_length=32)] | None = None


class ScreeningResponse(ScreeningInput):
    model_config = ConfigDict(from_attributes=True)
    reviewed_at: datetime | None


class ReviewHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    action: str
    from_status: VerificationStatus | None
    to_status: VerificationStatus
    reviewed_by: UUID
    notes: str | None
    created_at: datetime


class VerificationDetailResponse(BaseModel):
    interviewer_id: UUID
    status: VerificationStatus
    submitted_at: datetime | None
    reviewed_at: datetime | None
    rejection_reason: str | None
    suspension_reason: str | None
    evidence: list[EvidenceResponse]
    checks: list[VerificationCheckResponse]
    screening: ScreeningResponse | None
    history: list[ReviewHistoryResponse] = Field(default_factory=list)
    account_email: EmailStr | None = None
    account_email_verified: bool = False
    mobile_e164: str | None = None
    mobile_verified: bool = False
    company_email: EmailStr | None = None
    company_email_verified: bool = False
    missing_requirements: list[VerificationCheckType] = Field(default_factory=list)


class MobileVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mobile: Annotated[str, Field(min_length=8, max_length=32)]


class CompanyEmailVerificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_email: EmailStr


class ChallengeVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    secret: Annotated[str, Field(min_length=6, max_length=128)]


class ChallengeResponse(BaseModel):
    challenge_id: UUID
    expires_at: datetime
    resend_available_at: datetime
    development_secret: str | None = None


class VerificationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "under_review", "verify", "reject", "request_more_evidence", "suspend", "reactivate"
    ]
    reason: Annotated[str, Field(max_length=1000)] | None = None
    checks: dict[VerificationCheckType, bool] = Field(default_factory=dict)
    evidence_statuses: dict[UUID, EvidenceStatus] = Field(default_factory=dict)
    screening: ScreeningInput | None = None


class EvidenceReviewRequest(BaseModel):
    status: EvidenceStatus
    notes: Annotated[str, Field(max_length=2000)] | None = None


class ScreeningReviewRequest(ScreeningInput):
    pass


class InterviewerDeleteRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=1000)]


class CandidateTrustResponse(BaseModel):
    interviewer_id: UUID
    roundready_verified: bool
    contact_verified: bool
    professional_experience_reviewed: bool
    screening_passed: bool


class PublicInterviewerResponse(BaseModel):
    interviewer_id: UUID
    full_name: str | None
    headline: str
    job_title: str | None
    experience_years: Decimal
    bio: str | None
    skills: list[SkillResponse]
    interview_languages: list[str] = Field(default_factory=lambda: ["English"])
    roundready_verified: bool = True
    contact_verified: bool
    professional_experience_reviewed: bool
    screening_passed: bool
    price_paise: int = 20000
    currency: Literal["INR"] = "INR"
