from datetime import datetime, time
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.domain.models import VerificationStatus
from pydantic import (
    BaseModel,
    ConfigDict,
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

    headline: Annotated[NonBlank, Field(max_length=180)]
    company: Annotated[NonBlank, Field(max_length=160)] | None = None
    job_title: Annotated[NonBlank, Field(max_length=160)] | None = None
    experience_years: Decimal = Field(default=Decimal("0.0"), ge=0, le=60, decimal_places=1)
    linkedin_url: HttpUrl | None = None
    github_url: HttpUrl | None = None
    bio: Annotated[NonBlank, Field(max_length=4000)] | None = None

    @field_validator("linkedin_url")
    @classmethod
    def linkedin_host(cls, value: HttpUrl | None) -> HttpUrl | None:
        host = value.host if value else None
        if host and host != "linkedin.com" and not host.endswith(".linkedin.com"):
            raise ValueError("linkedin_url must use a linkedin.com host")
        return value

    @field_validator("github_url")
    @classmethod
    def github_host(cls, value: HttpUrl | None) -> HttpUrl | None:
        if value and value.host not in {"github.com", "www.github.com"}:
            raise ValueError("github_url must use a github.com host")
        return value


class ProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
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
