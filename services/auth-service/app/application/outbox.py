from datetime import UTC, datetime

from app.domain.models import OutboxEvent
from roundready_common.events import EventEnvelope
from roundready_common.messaging import RabbitEventPublisher
from roundready_common.metrics import record_outbox
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def publish_pending_events(
    session: AsyncSession, publisher: RabbitEventPublisher, *, batch_size: int = 100
) -> int:
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.published_at.is_(None))
        .order_by(OutboxEvent.occurred_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(result.scalars())
    published = 0
    for record in events:
        record.publish_attempts += 1
        envelope = EventEnvelope(
            event_id=record.id,
            event_type=record.event_type,
            event_version=record.event_version,
            occurred_at=record.occurred_at,
            correlation_id=record.correlation_id,
            producer="auth-service",
            payload=record.payload,
        )
        try:
            await publisher.publish(envelope)
        except Exception as exc:
            record.last_error = type(exc).__name__
            await session.commit()
            record_outbox("failure")
            break
        record.published_at = datetime.now(UTC)
        record.last_error = None
        await session.commit()
        published += 1
        record_outbox("success")
    return published
