import asyncio

import structlog
from app.application.outbox import publish_pending_events
from app.config import get_settings
from app.infrastructure.database import session_factory
from roundready_common.logging import configure_logging
from roundready_common.messaging import RabbitEventPublisher


async def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.service_name, settings.environment)
    logger = structlog.get_logger(service=settings.service_name, worker="outbox")
    publisher = RabbitEventPublisher(settings.rabbitmq_url, settings.rabbitmq_exchange)
    while True:
        try:
            async with session_factory() as session:
                count = await publish_pending_events(session, publisher)
            if count:
                logger.info("outbox_batch_published", event_count=count)
        except Exception as exc:
            logger.error("outbox_publish_failed", error_type=type(exc).__name__)
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(run())
