from typing import Protocol


class NotificationProvider(Protocol):
    async def send(self, *, recipient: str, template: str, context: dict[str, object]) -> str: ...
