import asyncio
from uuid import UUID

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage
from app.application.auth_service import AuthService
from app.config import get_settings
from app.infrastructure.database import session_factory
from roundready_common.logging import configure_logging
from roundready_common.messaging import connect_rabbit, decode_event
from sqlalchemy.exc import OperationalError

EVENT_STATES = {
    "interviewer.verification.approved.v1": "active",
    "interviewer.verification.suspended.v1": "blocked",
    "interviewer.deleted.v1": "disabled",
}


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    logger = structlog.get_logger(service=settings.service_name, worker="interviewer-events")
    connection = await connect_rabbit(settings.rabbitmq_url)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=20)
    exchange = await channel.declare_exchange(
        settings.rabbitmq_exchange, aio_pika.ExchangeType.TOPIC, durable=True
    )
    await channel.declare_exchange(
        settings.rabbitmq_dead_letter_exchange, aio_pika.ExchangeType.TOPIC, durable=True
    )
    queue = await channel.declare_queue(
        settings.rabbitmq_queue,
        durable=True,
        arguments={"x-dead-letter-exchange": settings.rabbitmq_dead_letter_exchange},
    )
    for event_type in EVENT_STATES:
        await queue.bind(exchange, routing_key=event_type)

    async def handle(message: AbstractIncomingMessage) -> None:
        try:
            event = decode_event(message.body)
            user_id = UUID(str(event.payload["interviewer_id"]))
            async with session_factory() as session:
                await AuthService(session, settings).apply_interviewer_access_event(
                    event.event_id,
                    user_id,
                    EVENT_STATES[event.event_type],
                    event.occurred_at,
                    str(event.payload["reason_category"])
                    if event.payload.get("reason_category")
                    else None,
                )
        except (ConnectionError, LookupError, OSError, OperationalError, TimeoutError) as exc:
            await message.nack(requeue=True)
            logger.warning("interviewer_access_event_requeued", error_type=type(exc).__name__)
            return
        except Exception as exc:
            await message.reject(requeue=False)
            logger.error("interviewer_access_event_rejected", error_type=type(exc).__name__)
            return
        await message.ack()
        logger.info("interviewer_access_event_consumed", event_id=str(event.event_id))

    await queue.consume(handle)
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
