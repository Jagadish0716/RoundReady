from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.application.notification_service import NotificationService
from app.config import get_settings
from app.domain.models import (
    Channel,
    DeadLetterRecord,
    DeliveryAttempt,
    DeliveryStatus,
    Notification,
    ProcessedEvent,
)
from app.domain.templates import TEMPLATES, TemplateError
from conftest import EMAIL, WHATSAPP
from fastapi.testclient import TestClient
from roundready_common.events import EventEnvelope
from roundready_common.messaging import decode_event
from sqlalchemy import func, select


def event(event_type: str = "BookingConfirmed", **payload) -> EventEnvelope:
    base = {
        "recipient_email": "candidate@example.com",
        "recipient_whatsapp": "+919999999999",
        "recipient_name": "Candidate",
        "scheduled_start": "2026-09-01T10:00:00Z",
        "booking_id": str(uuid4()),
        "session_id": str(uuid4()),
        "amount_paise": 20000,
        "minutes_until_start": 10,
    }
    base.update(payload)
    return EventEnvelope(
        event_type=event_type,
        event_version=1,
        producer="test",
        correlation_id=f"corr-{uuid4()}",
        payload=base,
    )


async def consume(value: EventEnvelope):
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        return await NotificationService(
            session, {Channel.EMAIL: EMAIL, Channel.WHATSAPP: WHATSAPP}, get_settings()
        ).consume(value)


async def get_notification(event_id: UUID, channel: Channel = Channel.EMAIL) -> Notification:
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        result = await session.scalar(
            select(Notification).where(
                Notification.event_id == event_id, Notification.channel == channel
            )
        )
        assert result
        return result


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}


def test_recipient_dependency_retry_classification(client: TestClient) -> None:
    from app.workers.consumer import retryable_recipient_error

    request = httpx.Request("GET", "http://user-service")
    assert retryable_recipient_error(httpx.ConnectError("down", request=request))
    assert retryable_recipient_error(
        httpx.HTTPStatusError(
            "unavailable", request=request, response=httpx.Response(503, request=request)
        )
    )
    assert not retryable_recipient_error(
        httpx.HTTPStatusError(
            "not found", request=request, response=httpx.Response(404, request=request)
        )
    )


@pytest.mark.asyncio
async def test_event_consumption_and_successful_delivery(client: TestClient) -> None:
    value = decode_event(event().model_dump_json().encode())
    records = await consume(value)
    assert len(records) == 2 and {x.status for x in records} == {DeliveryStatus.SENT}
    assert len(EMAIL.messages) == 1 and len(WHATSAPP.messages) == 1
    assert EMAIL.messages[0].idempotency_key == str(records[0].id)


@pytest.mark.asyncio
async def test_duplicate_event_is_idempotent(client: TestClient) -> None:
    value = event()
    await consume(value)
    await consume(value)
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.event_id == value.event_id)
        )
        processed = await session.get(ProcessedEvent, value.event_id)
    assert count == 2 and processed is not None and len(EMAIL.messages) == 1


@pytest.mark.asyncio
async def test_versioned_booking_event_contract_is_consumed(client: TestClient) -> None:
    value = event("booking.confirmed.v1", recipient_whatsapp=None)
    records = await consume(value)
    assert len(records) == 1 and records[0].template == "booking_confirmed"


@pytest.mark.asyncio
async def test_provider_failure_schedules_exponential_retry(client: TestClient) -> None:
    EMAIL.failures_remaining = 1
    value = event(recipient_whatsapp=None)
    await consume(value)
    record = await get_notification(value.event_id)
    assert record.status is DeliveryStatus.RETRY_SCHEDULED and record.attempt_count == 1
    first_retry = record.next_attempt_at
    assert first_retry is not None
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        service = NotificationService(
            session, {Channel.EMAIL: EMAIL, Channel.WHATSAPP: WHATSAPP}, get_settings()
        )
        assert await service.retry_due(first_retry + timedelta(milliseconds=1)) == 1
    record = await get_notification(value.event_id)
    assert record.status is DeliveryStatus.SENT and record.attempt_count == 2


@pytest.mark.asyncio
async def test_exhausted_retries_are_dead_lettered(client: TestClient) -> None:
    EMAIL.failures_remaining = 10
    value = event(recipient_whatsapp=None)
    await consume(value)
    from app.infrastructure.database import session_factory

    for offset in (2, 10):
        async with session_factory() as session:
            await NotificationService(
                session, {Channel.EMAIL: EMAIL, Channel.WHATSAPP: WHATSAPP}, get_settings()
            ).retry_due(datetime.now(UTC) + timedelta(seconds=offset))
    record = await get_notification(value.event_id)
    assert record.status is DeliveryStatus.DEAD_LETTERED and record.attempt_count == 3
    async with session_factory() as session:
        dead = await session.scalar(
            select(DeadLetterRecord).where(DeadLetterRecord.notification_id == record.id)
        )
        attempts = await session.scalar(
            select(func.count())
            .select_from(DeliveryAttempt)
            .where(DeliveryAttempt.notification_id == record.id)
        )
    assert dead is not None and dead.reason_code == "delivery_attempts_exhausted" and attempts == 3


@pytest.mark.asyncio
async def test_unsupported_and_recipient_missing_events_dead_letter(client: TestClient) -> None:
    unsupported = event("SomethingElse")
    missing = event(recipient_email=None, recipient_whatsapp=None)
    assert await consume(unsupported) == [] and await consume(missing) == []
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        reasons = set(
            (
                await session.scalars(
                    select(DeadLetterRecord.reason_code).where(
                        DeadLetterRecord.event_id.in_([unsupported.event_id, missing.event_id])
                    )
                )
            ).all()
        )
    assert reasons == {"unsupported_event", "recipient_missing"}


@pytest.mark.asyncio
@pytest.mark.parametrize("event_type", list(TEMPLATES))
async def test_all_notification_templates_render(client: TestClient, event_type: str) -> None:
    value = event(event_type, recipient_whatsapp=None)
    records = await consume(value)
    assert len(records) == 1 and records[0].rendered_body and "{" not in records[0].rendered_body


def test_template_missing_context_is_rejected() -> None:
    with pytest.raises(TemplateError):
        TEMPLATES["BookingConfirmed"].render({"recipient_name": "Candidate"})


@pytest.mark.asyncio
async def test_correlation_id_and_provider_reference_persist(client: TestClient) -> None:
    value = event(recipient_whatsapp=None)
    records = await consume(value)
    record = await get_notification(value.event_id)
    assert (
        record.correlation_id == value.correlation_id
        and record.provider_reference is not None
        and records[0].sent_at is not None
    )
