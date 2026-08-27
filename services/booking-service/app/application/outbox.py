from datetime import UTC, datetime

from app.domain.models import OutboxEvent
from roundready_common.events import EventEnvelope
from roundready_common.messaging import RabbitEventPublisher
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def publish_pending(session: AsyncSession, publisher: RabbitEventPublisher) -> int:
    records = list(
        (
            await session.scalars(
                select(OutboxEvent)
                .where(OutboxEvent.published_at.is_(None))
                .order_by(OutboxEvent.occurred_at)
                .limit(100)
                .with_for_update(skip_locked=True)
            )
        ).all()
    )
    count = 0
    for record in records:
        record.publish_attempts += 1
        try:
            await publisher.publish(
                EventEnvelope(
                    event_id=record.id,
                    event_type=record.event_type,
                    event_version=record.event_version,
                    occurred_at=record.occurred_at,
                    correlation_id=record.correlation_id,
                    producer="booking-service",
                    payload=record.payload,
                )
            )
        except Exception as exc:
            record.last_error = type(exc).__name__
            await session.commit()
            break
        record.published_at = datetime.now(UTC)
        record.last_error = None
        await session.commit()
        count += 1
    return count
