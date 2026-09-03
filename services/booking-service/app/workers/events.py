import asyncio
from uuid import UUID

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage
from app.application.booking_service import BookingService
from app.config import get_settings
from app.infrastructure.database import session_factory
from app.infrastructure.holds import RedisHoldStore
from redis.exceptions import RedisError
from roundready_common.contracts import PAYMENT_CAPTURED, PAYMENT_FAILED, PAYMENT_REFUNDED
from roundready_common.logging import configure_logging
from roundready_common.messaging import connect_rabbit, decode_event
from roundready_common.redis import create_redis_client
from sqlalchemy.exc import OperationalError


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    logger = structlog.get_logger(service=settings.service_name, worker="payment-events")
    redis = create_redis_client(settings.redis_url)
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
    for event_type in (PAYMENT_CAPTURED, PAYMENT_FAILED, PAYMENT_REFUNDED):
        await queue.bind(exchange, routing_key=event_type)

    async def handle(message: AbstractIncomingMessage) -> None:
        try:
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
        except (ConnectionError, OSError, TimeoutError, RedisError, OperationalError) as exc:
            await message.nack(requeue=True)
            logger.warning("payment_event_requeued", error_type=type(exc).__name__)
            return
        except Exception as exc:
            await message.reject(requeue=False)
            logger.error("payment_event_rejected", error_type=type(exc).__name__)
            return
        await message.ack()
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
