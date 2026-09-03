import json
from collections.abc import Awaitable, Callable

import aio_pika
from opentelemetry import trace

from roundready_common.events import EventEnvelope
from roundready_common.metrics import record_broker

EventHandler = Callable[[EventEnvelope], Awaitable[None]]

RABBITMQ_CONNECTION_TIMEOUT_SECONDS = 10
RABBITMQ_RECONNECT_INTERVAL_SECONDS = 5


async def connect_rabbit(url: str) -> aio_pika.abc.AbstractRobustConnection:
    return await aio_pika.connect_robust(
        url,
        timeout=RABBITMQ_CONNECTION_TIMEOUT_SECONDS,
        reconnect_interval=RABBITMQ_RECONNECT_INTERVAL_SECONDS,
        fail_fast=False,
    )


class RabbitEventPublisher:
    def __init__(self, url: str, exchange_name: str = "roundready.events") -> None:
        self._url = url
        self._exchange_name = exchange_name

    async def publish(self, event: EventEnvelope) -> None:
        tracer = trace.get_tracer(__name__)
        try:
            with tracer.start_as_current_span("rabbitmq.publish") as span:
                span.set_attribute("messaging.destination.name", self._exchange_name)
                span.set_attribute("messaging.rabbitmq.routing_key", event.event_type)
                span.set_attribute("roundready.correlation_id", event.correlation_id)
                connection = await connect_rabbit(self._url)
                async with connection:
                    channel = await connection.channel(publisher_confirms=True)
                    exchange = await channel.declare_exchange(
                        self._exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
                    )
                    message = aio_pika.Message(
                        body=event.model_dump_json().encode(),
                        content_type="application/json",
                        delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                        message_id=str(event.event_id),
                        correlation_id=event.correlation_id,
                    )
                    await exchange.publish(message, routing_key=event.event_type)
            record_broker("publish", "success")
        except Exception:
            record_broker("publish", "failure")
            raise


def decode_event(body: bytes) -> EventEnvelope:
    return EventEnvelope.model_validate(json.loads(body))
