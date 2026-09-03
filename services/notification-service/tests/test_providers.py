import json

import httpx
import pytest
from app.domain.providers import ProviderMessage
from app.infrastructure.providers import MetaWhatsAppProvider, ResendEmailProvider

MESSAGE = ProviderMessage(
    recipient="candidate@example.com",
    subject="RoundReady update",
    body="Your interview is confirmed.",
    idempotency_key="notification-id",
)


def email_provider(transport: httpx.AsyncBaseTransport) -> ResendEmailProvider:
    return ResendEmailProvider(
        "https://api.resend.com",
        "server-email-api-key",
        "notifications@roundready.example",
        10,
        transport=transport,
    )


def whatsapp_provider(transport: httpx.AsyncBaseTransport) -> MetaWhatsAppProvider:
    return MetaWhatsAppProvider(
        "https://graph.facebook.com/v23.0",
        "server-whatsapp-token",
        "123456789",
        "roundready_notification",
        "en",
        10,
        transport=transport,
    )


@pytest.mark.asyncio
async def test_resend_email_success() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer server-email-api-key"
        assert request.headers["Idempotency-Key"] == MESSAGE.idempotency_key
        data = json.loads(request.content)
        assert data["to"] == [MESSAGE.recipient]
        assert data["subject"] == MESSAGE.subject and data["text"] == MESSAGE.body
        return httpx.Response(200, json={"id": "email-reference"})

    reference = await email_provider(httpx.MockTransport(handler)).send(MESSAGE)
    assert reference == "email-reference"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 503])
async def test_resend_email_provider_errors(status: int) -> None:
    provider = email_provider(httpx.MockTransport(lambda _request: httpx.Response(status)))
    with pytest.raises(httpx.HTTPStatusError):
        await provider.send(MESSAGE)


@pytest.mark.asyncio
async def test_resend_email_timeout() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("unavailable", request=request)

    with pytest.raises(httpx.ConnectTimeout):
        await email_provider(httpx.MockTransport(timeout)).send(MESSAGE)


@pytest.mark.asyncio
async def test_resend_email_malformed_response() -> None:
    provider = email_provider(httpx.MockTransport(lambda _request: httpx.Response(200, json={})))
    with pytest.raises(ValueError, match="invalid response"):
        await provider.send(MESSAGE)


def test_resend_email_requires_configuration() -> None:
    with pytest.raises(ValueError, match="configuration"):
        ResendEmailProvider("", "", "", 10)


@pytest.mark.asyncio
async def test_meta_whatsapp_success() -> None:
    message = ProviderMessage(
        recipient="+919999999999",
        subject=None,
        body="Your feedback is available.",
        idempotency_key="notification-id",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer server-whatsapp-token"
        data = json.loads(request.content)
        assert data["to"] == "919999999999"
        assert data["type"] == "template"
        assert data["template"]["name"] == "roundready_notification"
        assert data["template"]["components"][0]["parameters"][0]["text"] == message.body
        return httpx.Response(200, json={"messages": [{"id": "whatsapp-reference"}]})

    reference = await whatsapp_provider(httpx.MockTransport(handler)).send(message)
    assert reference == "whatsapp-reference"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [400, 503])
async def test_meta_whatsapp_provider_rejection(status: int) -> None:
    provider = whatsapp_provider(httpx.MockTransport(lambda _request: httpx.Response(status)))
    with pytest.raises(httpx.HTTPStatusError):
        await provider.send(MESSAGE)


@pytest.mark.asyncio
async def test_meta_whatsapp_timeout() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("unavailable", request=request)

    with pytest.raises(httpx.ConnectTimeout):
        await whatsapp_provider(httpx.MockTransport(timeout)).send(MESSAGE)


@pytest.mark.asyncio
async def test_meta_whatsapp_malformed_response() -> None:
    provider = whatsapp_provider(
        httpx.MockTransport(lambda _request: httpx.Response(200, json={"messages": []}))
    )
    with pytest.raises(ValueError, match="invalid response"):
        await provider.send(MESSAGE)


def test_meta_whatsapp_requires_configuration() -> None:
    with pytest.raises(ValueError, match="configuration"):
        MetaWhatsAppProvider("", "", "", "", "", 10)
