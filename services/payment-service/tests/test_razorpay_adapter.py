import hashlib
import hmac

import httpx
import pytest
from app.infrastructure.razorpay import RazorpayAdapter


def test_webhook_signature_verification() -> None:
    adapter = RazorpayAdapter(
        "rzp_test_key", "key-secret", "webhook-secret", "https://api.razorpay.com/v1", True
    )
    body = b'{"event":"payment.captured"}'
    signature = hmac.new(b"webhook-secret", body, hashlib.sha256).hexdigest()
    assert adapter.verify_webhook(body, signature)
    assert not adapter.verify_webhook(body, "bad-signature")


def test_key_mode_must_match_configuration() -> None:
    with pytest.raises(ValueError, match="configured mode"):
        RazorpayAdapter(
            "rzp_test_key", "key-secret", "webhook-secret", "https://api.razorpay.com/v1", False
        )


@pytest.mark.asyncio
async def test_production_order_uses_authoritative_amount_and_public_checkout_data() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/orders"
        assert request.headers["Authorization"].startswith("Basic ")
        body = request.content.decode()
        assert '"amount":20000' in body and '"currency":"INR"' in body
        return httpx.Response(
            200,
            json={"id": "order_live_123", "amount": 20000, "currency": "INR"},
        )

    adapter = RazorpayAdapter(
        "rzp_live_public_key",
        "server-key-secret",
        "server-webhook-secret",
        "https://api.razorpay.com/v1",
        False,
        transport=httpx.MockTransport(handler),
    )
    order = await adapter.create_order(
        amount_paise=20000, currency="INR", idempotency_key="order-idempotency-key"
    )
    assert order.order_id == "order_live_123"
    assert order.amount_paise == 20000 and order.currency == "INR"
    assert order.checkout_data == {
        "key_id": "rzp_live_public_key",
        "order_id": "order_live_123",
        "amount": 20000,
        "currency": "INR",
    }
    assert "secret" not in repr(order.checkout_data).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, text="not-json"), httpx.Response(200, json={"id": "incomplete"})],
)
async def test_invalid_provider_response_is_rejected(response: httpx.Response) -> None:
    adapter = RazorpayAdapter(
        "rzp_live_public_key",
        "server-key-secret",
        "server-webhook-secret",
        "https://api.razorpay.com/v1",
        False,
        transport=httpx.MockTransport(lambda _request: response),
    )
    with pytest.raises(ValueError, match="Razorpay returned"):
        await adapter.create_order(amount_paise=20000, currency="INR", idempotency_key="idem")


@pytest.mark.asyncio
async def test_provider_network_failure_is_propagated_for_controlled_service_mapping() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("provider unavailable", request=request)

    adapter = RazorpayAdapter(
        "rzp_live_public_key",
        "server-key-secret",
        "server-webhook-secret",
        "https://api.razorpay.com/v1",
        False,
        transport=httpx.MockTransport(timeout),
    )
    with pytest.raises(httpx.ConnectTimeout):
        await adapter.create_order(amount_paise=20000, currency="INR", idempotency_key="idem")
