import asyncio
from datetime import datetime
from uuid import UUID

import aio_pika
import structlog
from aio_pika.abc import AbstractIncomingMessage
from roundready_common.contracts import BOOKING_CONFIRMED
from roundready_common.logging import configure_logging
from roundready_common.messaging import decode_event

from app.api.schemas import SessionCreate
from app.application.interview_service import InterviewService
from app.config import get_settings
from app.domain.providers import VideoProvider
from app.infrastructure.database import session_factory
from app.infrastructure.development import DevelopmentVideoProvider
from app.infrastructure.livekit import LiveKitDevelopmentAdapter


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(service=settings.service_name, worker="booking-events")
    provider: VideoProvider
    if settings.video_provider == "development":
        provider = DevelopmentVideoProvider(
            settings.livekit_url,
            settings.livekit_api_key.get_secret_value(),
            settings.livekit_api_secret.get_secret_value(),
            settings.participant_token_ttl_seconds,
        )
    else:
        provider = LiveKitDevelopmentAdapter(
            settings.livekit_url,
            settings.livekit_api_key.get_secret_value(),
            settings.livekit_api_secret.get_secret_value(),
            settings.participant_token_ttl_seconds,
            settings.livekit_test_mode,
        )
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
    await queue.bind(exchange, routing_key=BOOKING_CONFIRMED)

    async def handle(message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=False):
            event = decode_event(message.body)
            payload = event.payload
            data = SessionCreate(
                event_id=event.event_id,
                booking_id=UUID(str(payload["booking_id"])),
                candidate_id=UUID(str(payload["candidate_id"])),
                interviewer_id=UUID(str(payload["interviewer_id"])),
                rubric_id=UUID(str(payload["rubric_id"])),
                scheduled_start=datetime.fromisoformat(str(payload["scheduled_start"])),
                scheduled_end=datetime.fromisoformat(str(payload["scheduled_end"])),
            )
            async with session_factory() as session:
                await InterviewService(session, provider, settings).create_session(data)
            logger.info(
                "booking_event_consumed",
                event_id=str(event.event_id),
                correlation_id=event.correlation_id,
            )

    await queue.consume(handle)
    try:
        await asyncio.Future()
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run())
