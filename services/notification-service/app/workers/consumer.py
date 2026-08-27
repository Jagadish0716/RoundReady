import asyncio

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage
from roundready_common.logging import configure_logging
from roundready_common.messaging import decode_event

from app.application.notification_service import NotificationService
from app.config import Settings, get_settings
from app.domain.models import Channel
from app.domain.providers import NotificationProvider
from app.domain.templates import supported_event_types
from app.infrastructure.database import session_factory
from app.infrastructure.providers import DevelopmentEmailProvider, DevelopmentWhatsAppProvider


def providers() -> dict[Channel, NotificationProvider]:
    return {
        Channel.EMAIL: DevelopmentEmailProvider(),
        Channel.WHATSAPP: DevelopmentWhatsAppProvider(),
    }


async def retry_loop(settings: Settings) -> None:
    logger = structlog.get_logger(service=settings.service_name, worker="delivery-retry")
    while True:
        try:
            async with session_factory() as session:
                sent = await NotificationService(session, providers(), settings).retry_due()
            if sent:
                logger.info("notification_retry_batch", sent=sent)
        except Exception as exc:
            logger.error("notification_retry_failed", error_type=type(exc).__name__)
        await asyncio.sleep(1)


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(service=settings.service_name, worker="event-consumer")
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
        arguments={
            "x-dead-letter-exchange": settings.rabbitmq_dead_letter_exchange,
            "x-dead-letter-routing-key": "notification.dead",
        },
    )
    for event_type in supported_event_types():
        await queue.bind(exchange, routing_key=event_type)

    async def handle(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            event = decode_event(message.body)
            async with session_factory() as session:
                await NotificationService(session, providers(), settings).consume(event)
            logger.info(
                "notification_event_consumed",
                event_id=str(event.event_id),
                event_type=event.event_type,
                correlation_id=event.correlation_id,
            )

    await queue.consume(handle)
    retry_task = asyncio.create_task(retry_loop(settings))
    try:
        await asyncio.Future()
    finally:
        retry_task.cancel()
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
