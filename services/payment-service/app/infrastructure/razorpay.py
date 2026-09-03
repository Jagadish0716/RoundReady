import hashlib
import hmac
from typing import Any

import httpx
from app.domain.providers import ProviderOrder, ProviderRefund


class RazorpayAdapter:
    name = "razorpay"

    def __init__(
        self,
        key_id: str,
        key_secret: str,
        webhook_secret: str,
        base_url: str,
        test_mode: bool,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        expected_prefix = "rzp_test_" if test_mode else "rzp_live_"
        if not key_id.startswith(expected_prefix):
            raise ValueError("Razorpay key ID does not match the configured mode")
        if not key_secret or not webhook_secret:
            raise ValueError("Razorpay secrets are required")
        self._key_id, self._key_secret = key_id, key_secret
        self._webhook_secret, self._base_url = webhook_secret, base_url.rstrip("/")
        self._transport = transport

    async def create_order(
        self, *, amount_paise: int, currency: str, idempotency_key: str
    ) -> ProviderOrder:
        receipt = hashlib.sha256(idempotency_key.encode()).hexdigest()[:40]
        async with self._client() as client:
            response = await client.post(
                f"{self._base_url}/orders",
                json={"amount": amount_paise, "currency": currency, "receipt": receipt},
            )
            response.raise_for_status()
            data = self._object(response)
        order_id = self._string(data, "id")
        provider_amount = self._integer(data, "amount")
        provider_currency = self._string(data, "currency")
        return ProviderOrder(
            order_id,
            provider_amount,
            provider_currency,
            {
                "key_id": self._key_id,
                "order_id": order_id,
                "amount": amount_paise,
                "currency": currency,
            },
        )

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def refund(
        self, *, provider_payment_id: str, amount_paise: int, idempotency_key: str
    ) -> ProviderRefund:
        async with self._client() as client:
            response = await client.post(
                f"{self._base_url}/payments/{provider_payment_id}/refund",
                json={"amount": amount_paise, "notes": {"idempotency_key": idempotency_key}},
            )
            response.raise_for_status()
            data = self._object(response)
        return ProviderRefund(self._string(data, "id"), self._string(data, "status") == "processed")

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=(self._key_id, self._key_secret),
            timeout=httpx.Timeout(10.0, connect=5.0),
            transport=self._transport,
        )

    @staticmethod
    def _object(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as exc:
            raise ValueError("Razorpay returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("Razorpay returned an invalid response")
        return value

    @staticmethod
    def _string(value: dict[str, Any], key: str) -> str:
        result = value.get(key)
        if not isinstance(result, str) or not result:
            raise ValueError("Razorpay returned an invalid response")
        return result

    @staticmethod
    def _integer(value: dict[str, Any], key: str) -> int:
        result = value.get(key)
        if not isinstance(result, int) or isinstance(result, bool):
            raise ValueError("Razorpay returned an invalid response")
        return result


# Backward-compatible import for existing integrations while they migrate to the neutral name.
RazorpayTestAdapter = RazorpayAdapter
