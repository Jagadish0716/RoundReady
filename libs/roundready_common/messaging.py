import json
from collections.abc import Awaitable, Callable

import aio_pika

from roundready_common.events import EventEnvelope

EventHandler = Callable[[EventEnvelope], Awaitable[None]]


class RabbitEventPublisher:
    def __init__(self, url: str, exchange_name: str = "roundready.events") -> None:
        self._url = url
        self._exchange_name = exchange_name

    async def publish(self, event: EventEnvelope) -> None:
        connection = await aio_pika.connect_robust(self._url)
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


def decode_event(body: bytes) -> EventEnvelope:
    return EventEnvelope.model_validate(json.loads(body))
