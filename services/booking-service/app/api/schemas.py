from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.domain.models import BookingStatus, SlotStatus
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SlotWindow(BaseModel):
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def valid(self) -> "SlotWindow":
        if (
            self.starts_at.tzinfo is None
            or self.ends_at.tzinfo is None
            or self.starts_at >= self.ends_at
        ):
            raise ValueError("slot window must be timezone-aware and increasing")
        return self


class GenerateSlotsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    interviewer_id: UUID
    rubric_id: UUID
    domain: Annotated[str, Field(min_length=1, max_length=80)]
    topic: Annotated[str, Field(min_length=1, max_length=120)]
    experience_level: Annotated[str, Field(min_length=1, max_length=40)]
    windows: list[SlotWindow] = Field(min_length=1, max_length=500)


class SlotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    interviewer_id: UUID
    rubric_id: UUID
    domain: str
    topic: str
    experience_level: str
    starts_at: datetime
    ends_at: datetime
    status: SlotStatus
    hold_expires_at: datetime | None


class HoldResponse(BaseModel):
    slot_id: UUID
    hold_token: str
    expires_at: datetime


class BookingCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot_id: UUID
    hold_token: Annotated[str, Field(min_length=32, max_length=256)]


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    slot_id: UUID
    candidate_id: UUID
    interviewer_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: BookingStatus
    amount_paise: int
    currency: str
    created_at: datetime
    updated_at: datetime


class TransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: BookingStatus
    reason: Annotated[str, Field(max_length=500)] | None = None


class PaymentEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: UUID
    payment_id: UUID
    booking_id: UUID
    event_type: Annotated[str, Field(pattern=r"^payment\.(captured|failed|refunded)\.v1$")]
    amount_paise: Annotated[int, Field(ge=1)]
    currency: Annotated[str, Field(pattern=r"^INR$")]
