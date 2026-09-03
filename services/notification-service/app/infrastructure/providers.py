from uuid import uuid4

import httpx
from app.domain.providers import ProviderMessage


class DevelopmentEmailProvider:
    channel = "email"

    async def send(self, message: ProviderMessage) -> str:
        _ = message
        return f"dev-email-{uuid4()}"


class DevelopmentWhatsAppProvider:
    channel = "whatsapp"

    async def send(self, message: ProviderMessage) -> str:
        _ = message
        return f"dev-whatsapp-{uuid4()}"


class ResendEmailProvider:
    channel = "email"

    def __init__(
        self,
        api_base_url: str,
        api_key: str,
        from_address: str,
        timeout_seconds: float,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_base_url or not api_key or not from_address:
            raise ValueError("Resend configuration is required")
        self._api_base_url = api_base_url.rstrip("/")
        self._api_key = api_key
        self._from_address = from_address
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5.0))
        self._transport = transport

    async def send(self, message: ProviderMessage) -> str:
        if not message.subject:
            raise ValueError("Email subject is required")
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(
                f"{self._api_base_url}/emails",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Idempotency-Key": message.idempotency_key,
                },
                json={
                    "from": self._from_address,
                    "to": [message.recipient],
                    "subject": message.subject,
                    "text": message.body,
                },
            )
            response.raise_for_status()
            return _provider_reference(response, "id")


class MetaWhatsAppProvider:
    channel = "whatsapp"

    def __init__(
        self,
        api_base_url: str,
        access_token: str,
        phone_number_id: str,
        template_name: str,
        template_language: str,
        timeout_seconds: float,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not all([api_base_url, access_token, phone_number_id, template_name, template_language]):
            raise ValueError("WhatsApp configuration is required")
        self._api_base_url = api_base_url.rstrip("/")
        self._access_token = access_token
        self._phone_number_id = phone_number_id
        self._template_name = template_name
        self._template_language = template_language
        self._timeout = httpx.Timeout(timeout_seconds, connect=min(timeout_seconds, 5.0))
        self._transport = transport

    async def send(self, message: ProviderMessage) -> str:
        async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
            response = await client.post(
                f"{self._api_base_url}/{self._phone_number_id}/messages",
                headers={"Authorization": f"Bearer {self._access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": message.recipient.removeprefix("+"),
                    "type": "template",
                    "template": {
                        "name": self._template_name,
                        "language": {"code": self._template_language},
                        "components": [
                            {
                                "type": "body",
                                "parameters": [{"type": "text", "text": message.body}],
                            }
                        ],
                    },
                    "biz_opaque_callback_data": message.idempotency_key,
                },
            )
            response.raise_for_status()
            return _provider_reference(response, "messages", list_item_key="id")


def _provider_reference(
    response: httpx.Response, key: str, *, list_item_key: str | None = None
) -> str:
    try:
        data = response.json()
    except ValueError as exc:
        raise ValueError("notification provider returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ValueError("notification provider returned an invalid response")
    value = data.get(key)
    if list_item_key is not None:
        value = value[0].get(list_item_key) if isinstance(value, list) and value else None
    if not isinstance(value, str) or not value:
        raise ValueError("notification provider returned an invalid response")
    return value
