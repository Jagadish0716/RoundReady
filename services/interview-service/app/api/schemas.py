from datetime import datetime
from uuid import UUID

from app.domain.models import ReadinessLevel, SessionStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Criterion(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=160)
    weight: int = Field(gt=0, le=100)
    maximum_score: int = Field(gt=0, le=100)


class RubricCreate(BaseModel):
    domain: str = Field(min_length=1, max_length=80)
    topic: str = Field(min_length=1, max_length=120)
    experience_level: str = Field(min_length=1, max_length=40)
    version: int = Field(ge=1)
    criteria: list[Criterion] = Field(min_length=1, max_length=30)

    @field_validator("criteria")
    @classmethod
    def valid_criteria(cls, value: list[Criterion]) -> list[Criterion]:
        if len({x.key for x in value}) != len(value):
            raise ValueError("criterion keys must be unique")
        if sum(x.weight for x in value) != 100:
            raise ValueError("criterion weights must total 100")
        return value


class RubricResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    domain: str
    topic: str
    experience_level: str
    version: int
    criteria: list[dict[str, object]]
    maximum_score: int
    active: bool


class SessionCreate(BaseModel):
    event_id: UUID
    booking_id: UUID
    candidate_id: UUID
    interviewer_id: UUID
    rubric_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime

    @model_validator(mode="after")
    def schedule(self) -> "SessionCreate":
        if (
            self.scheduled_start.tzinfo is None
            or self.scheduled_end.tzinfo is None
            or self.scheduled_start >= self.scheduled_end
        ):
            raise ValueError("a valid timezone-aware schedule is required")
        return self


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    candidate_id: UUID
    interviewer_id: UUID
    rubric_id: UUID
    scheduled_start: datetime
    scheduled_end: datetime
    actual_start: datetime | None
    actual_end: datetime | None
    total_duration_seconds: int
    status: SessionStatus


class JoinResponse(BaseModel):
    token: str
    expires_at: datetime
    join_url: str


class AttendanceRequest(BaseModel):
    provider_event_id: str = Field(min_length=1, max_length=255)
    user_id: UUID
    event_type: str
    occurred_at: datetime

    @field_validator("event_type")
    @classmethod
    def event(cls, value: str) -> str:
        if value not in {"joined", "left"}:
            raise ValueError("event_type must be joined or left")
        return value


class AttendanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: UUID
    role: str
    first_joined_at: datetime | None
    last_joined_at: datetime | None
    last_left_at: datetime | None
    connected: bool
    reconnect_count: int
    total_connected_seconds: int


class TransitionRequest(BaseModel):
    status: SessionStatus


class CriterionScore(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    score: int = Field(ge=0)


class FeedbackCreate(BaseModel):
    criterion_scores: list[CriterionScore] = Field(min_length=1, max_length=30)
    strengths: list[str] = Field(min_length=1, max_length=20)
    improvement_areas: list[str] = Field(min_length=1, max_length=20)
    summary: str = Field(min_length=10, max_length=4000)
    readiness_level: ReadinessLevel


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    criterion_scores: list[dict[str, object]]
    strengths: list[str]
    improvement_areas: list[str]
    summary: str
    readiness_level: ReadinessLevel
    total_score: int
    submitted_at: datetime
