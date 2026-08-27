import json
from typing import Annotated, cast
from uuid import UUID

from app.api.schemas import (
    CreateOrderRequest,
    PaymentResponse,
    RefundRequest,
    RefundResponse,
    WebhookResponse,
)
from app.application.payment_service import PaymentService
from app.dependencies import (
    AdminIdentity,
    AppSettings,
    AuthenticatedIdentity,
    CandidateIdentity,
    DatabaseSession,
    Provider,
)
from app.domain.models import Payment
from fastapi import APIRouter, Header, Request
from roundready_common.errors import ServiceError

router = APIRouter(prefix="/v1", tags=["payments"])


def service(session: DatabaseSession, provider: Provider, settings: AppSettings) -> PaymentService:
    return PaymentService(session, provider, settings.session_price_paise)


@router.post("/payments/orders", response_model=PaymentResponse, status_code=201)
async def create_order(
    request: CreateOrderRequest,
    identity: CandidateIdentity,
    session: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> PaymentResponse:
    payment, checkout = await service(session, provider, settings).create_order(
        request.booking_id, identity.user_id, idempotency_key
    )
    response = PaymentResponse.model_validate(payment)
    return response.model_copy(update={"checkout_data": checkout})


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    identity: AuthenticatedIdentity,
    session: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> Payment:
    return await service(session, provider, settings).get(
        payment_id, identity.user_id, identity.role.value == "admin"
    )


@router.post("/admin/payments/{payment_id}/refunds", response_model=RefundResponse, status_code=201)
async def refund(
    payment_id: UUID,
    request: RefundRequest,
    _admin: AdminIdentity,
    session: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> RefundResponse:
    value = await service(session, provider, settings).refund(
        payment_id, request.amount_paise, request.reason
    )
    return RefundResponse.model_validate(value)


@router.post("/webhooks/razorpay", response_model=WebhookResponse)
async def webhook(
    request: Request,
    session: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
    signature: Annotated[str, Header(alias="X-Razorpay-Signature")],
    event_id: Annotated[str, Header(alias="X-Razorpay-Event-Id", min_length=1, max_length=255)],
) -> WebhookResponse:
    body = await request.body()
    if not provider.verify_webhook(body, signature):
        raise ServiceError(
            code="invalid_webhook_signature",
            message="Webhook signature is invalid",
            status_code=401,
        )
    try:
        raw = json.loads(body)
        if not isinstance(raw, dict) or not isinstance(raw.get("event"), str):
            raise ValueError
        payload = cast(dict[str, object], raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ServiceError(
            code="invalid_webhook_payload", message="Webhook payload is invalid", status_code=400
        ) from exc
    duplicate, ignored = await service(session, provider, settings).process_webhook(
        event_id, str(payload["event"]), payload
    )
    return WebhookResponse(duplicate=duplicate, ignored=ignored)
