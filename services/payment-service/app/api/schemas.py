from datetime import datetime
from uuid import UUID

from app.domain.models import PaymentStatus, RefundStatus
from pydantic import BaseModel, ConfigDict, Field


class CreateOrderRequest(BaseModel):
    booking_id: UUID


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    booking_id: UUID
    amount_paise: int
    currency: str
    provider: str
    provider_order_id: str | None
    provider_payment_id: str | None
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime
    checkout_data: dict[str, str | int] | None = None


class RefundRequest(BaseModel):
    amount_paise: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=3, max_length=500)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    payment_id: UUID
    provider_refund_id: str | None
    amount_paise: int
    reason: str
    status: RefundStatus
    created_at: datetime


class WebhookResponse(BaseModel):
    accepted: bool = True
    duplicate: bool = False
    ignored: bool = False
