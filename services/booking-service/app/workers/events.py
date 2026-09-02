import asyncio
from uuid import UUID

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage
from app.application.booking_service import BookingService
from app.config import get_settings
from app.infrastructure.database import session_factory
from app.infrastructure.holds import RedisHoldStore
from redis.asyncio import Redis
from roundready_common.contracts import PAYMENT_CAPTURED, PAYMENT_FAILED, PAYMENT_REFUNDED
from roundready_common.logging import configure_logging
from roundready_common.messaging import decode_event


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(service=settings.service_name, worker="payment-events")
    redis = Redis.from_url(settings.redis_url)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
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
    for event_type in (PAYMENT_CAPTURED, PAYMENT_FAILED, PAYMENT_REFUNDED):
        await queue.bind(exchange, routing_key=event_type)

    async def handle(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            event = decode_event(message.body)
            payload = event.payload
            async with session_factory() as session:
                await BookingService(
                    session, RedisHoldStore(redis, settings.hold_ttl_seconds), settings
                ).handle_payment(
                    event.event_id,
                    event.event_type,
                    UUID(str(payload["payment_id"])),
                    UUID(str(payload["booking_id"])),
                    int(payload["amount_paise"]),
                    str(payload["currency"]),
                )
            logger.info(
                "payment_event_consumed",
                event_id=str(event.event_id),
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )

    await queue.consume(handle)
    try:
        await asyncio.Future()
    finally:
        await redis.aclose()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
