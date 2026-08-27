import asyncio

import structlog
from app.application.booking_service import BookingService
from app.application.outbox import publish_pending
from app.config import get_settings
from app.infrastructure.database import session_factory
from app.infrastructure.holds import RedisHoldStore
from redis.asyncio import Redis
from roundready_common.logging import configure_logging
from roundready_common.messaging import RabbitEventPublisher


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = structlog.get_logger(service=settings.service_name, worker="maintenance")
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    holds = RedisHoldStore(redis, settings.hold_ttl_seconds)
    publisher = RabbitEventPublisher(settings.rabbitmq_url, settings.rabbitmq_exchange)
    while True:
        try:
            async with session_factory() as session:
                expired = await BookingService(session, holds, settings).expire_holds()
                published = await publish_pending(session, publisher)
            if expired or published:
                logger.info("maintenance_batch", expired_holds=expired, published_events=published)
        except Exception as exc:
            logger.error("maintenance_failed", error_type=type(exc).__name__)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run())
