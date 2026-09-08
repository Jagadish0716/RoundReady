from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from app.api.schemas import (
    BookingCreateRequest,
    BookingResponse,
    GenerateSlotsRequest,
    HoldResponse,
    InterviewerEligibilityEventRequest,
    PaymentEventRequest,
    SlotResponse,
    TransitionRequest,
)
from app.application.booking_service import BookingService
from app.dependencies import (
    AdminIdentity,
    AppSettings,
    AuthIdentity,
    CandidateIdentity,
    DatabaseSession,
    HoldStore,
)
from app.domain.models import BookingStatus
from fastapi import APIRouter, Header, Query, Response
from roundready_common.errors import ServiceError

router = APIRouter(prefix="/v1", tags=["booking"])


def service(session: DatabaseSession, holds: HoldStore, settings: AppSettings) -> BookingService:
    return BookingService(session, holds, settings)


@router.get("/public/slots", response_model=list[SlotResponse])
async def public_slots(
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
    starts_after: Annotated[datetime | None, Query()] = None,
    ends_before: Annotated[datetime | None, Query()] = None,
    interviewer_id: Annotated[UUID | None, Query()] = None,
) -> list[SlotResponse]:
    starts_after = starts_after or datetime.now(UTC)
    ends_before = ends_before or starts_after + timedelta(days=30)
    slots = await service(session, holds, settings).available_slots(
        starts_after, ends_before, interviewer_id
    )
    return [SlotResponse.model_validate(item) for item in slots]


@router.get("/public/slots/{slot_id}", response_model=SlotResponse)
async def public_slot(
    slot_id: UUID,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> SlotResponse:
    return SlotResponse.model_validate(
        await service(session, holds, settings).available_slot(slot_id)
    )


@router.post("/internal/slots/generate", response_model=list[SlotResponse])
async def generate(
    request: GenerateSlotsRequest,
    _admin: AdminIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> list[SlotResponse]:
    return [
        SlotResponse.model_validate(x)
        for x in await service(session, holds, settings).generate_slots(request)
    ]


@router.get("/slots", response_model=list[SlotResponse])
async def slots(
    starts_after: Annotated[datetime, Query()],
    ends_before: Annotated[datetime, Query()],
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
    _identity: AuthIdentity,
) -> list[SlotResponse]:
    return [
        SlotResponse.model_validate(x)
        for x in await service(session, holds, settings).available_slots(starts_after, ends_before)
    ]


@router.post("/slots/{slot_id}/hold", response_model=HoldResponse)
async def hold(
    slot_id: UUID,
    identity: CandidateIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> HoldResponse:
    token, expires = await service(session, holds, settings).hold(slot_id, identity.user_id)
    return HoldResponse(slot_id=slot_id, hold_token=token, expires_at=expires)


@router.post("/bookings", response_model=BookingResponse, status_code=201)
async def create(
    request: BookingCreateRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
    identity: CandidateIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> BookingResponse:
    value = await service(session, holds, settings).create_booking(
        request.slot_id, identity.user_id, request.hold_token, idempotency_key
    )
    return BookingResponse.model_validate(value)


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_candidate_booking(
    booking_id: UUID,
    identity: CandidateIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> BookingResponse:
    value = await service(session, holds, settings).get_candidate_booking(
        booking_id, identity.user_id
    )
    return BookingResponse.model_validate(value)


@router.post("/admin/bookings/{booking_id}/transition", response_model=BookingResponse)
async def transition(
    booking_id: UUID,
    request: TransitionRequest,
    admin: AdminIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> BookingResponse:
    return BookingResponse.model_validate(
        await service(session, holds, settings).transition(
            booking_id, request.status, admin.user_id, request.reason
        )
    )


@router.post("/bookings/{booking_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    booking_id: UUID,
    request: TransitionRequest,
    identity: CandidateIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> BookingResponse:
    if request.status is not BookingStatus.CANCELLED:
        raise ServiceError(
            code="invalid_booking_transition",
            message="Candidate cancellation requires cancelled status",
            status_code=409,
        )
    value = await service(session, holds, settings).cancel_by_candidate(
        booking_id, identity.user_id, request.reason
    )
    return BookingResponse.model_validate(value)


@router.post("/internal/payment-events", response_model=BookingResponse)
async def payment(
    request: PaymentEventRequest,
    _admin: AdminIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> BookingResponse:
    return BookingResponse.model_validate(
        await service(session, holds, settings).handle_payment(
            request.event_id,
            request.event_type,
            request.payment_id,
            request.booking_id,
            request.amount_paise,
            request.currency,
        )
    )


@router.post("/internal/interviewer-verification-events", status_code=204)
async def interviewer_verification_event(
    request: InterviewerEligibilityEventRequest,
    _admin: AdminIdentity,
    session: DatabaseSession,
    holds: HoldStore,
    settings: AppSettings,
) -> Response:
    await service(session, holds, settings).set_interviewer_eligibility(
        request.event_id,
        request.interviewer_id,
        request.event_type == "interviewer.verification.approved.v1",
        request.event_type,
    )
    return Response(status_code=204)
