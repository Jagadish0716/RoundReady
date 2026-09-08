from dataclasses import dataclass
from typing import Protocol

import httpx
from app.config import Settings


class EmailSender(Protocol):
    async def send_verification(self, email: str, url: str, idempotency_key: str) -> None: ...


@dataclass
class DevelopmentEmailSender:
    async def send_verification(self, email: str, url: str, idempotency_key: str) -> None:
        _ = (email, url, idempotency_key)


class ResendEmailSender:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send_verification(self, email: str, url: str, idempotency_key: str) -> None:
        async with httpx.AsyncClient(timeout=self._settings.provider_timeout_seconds) as client:
            response = await client.post(
                f"{self._settings.resend_api_base_url.rstrip('/')}/emails",
                headers={
                    "Authorization": f"Bearer {self._settings.resend_api_key.get_secret_value()}",
                    "Idempotency-Key": idempotency_key,
                },
                json={
                    "from": self._settings.email_from_address,
                    "to": [email],
                    "subject": "Verify your RoundReady email",
                    "text": f"Verify your email by opening this one-time link: {url}",
                },
            )
            response.raise_for_status()


def email_sender(settings: Settings) -> EmailSender:
    if settings.email_provider == "development":
        return DevelopmentEmailSender()
    return ResendEmailSender(settings)
