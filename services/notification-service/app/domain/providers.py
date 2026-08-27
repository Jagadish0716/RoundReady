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
