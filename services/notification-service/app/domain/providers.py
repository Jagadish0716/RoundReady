from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderMessage:
    recipient: str
    subject: str | None
    body: str
    idempotency_key: str


class NotificationProvider(Protocol):
    channel: str

    async def send(self, message: ProviderMessage) -> str: ...


@dataclass(frozen=True)
class NotificationDestination:
    email: str | None
    phone: str | None


class RecipientResolver(Protocol):
    async def resolve(self, user_id: str, correlation_id: str) -> NotificationDestination: ...
