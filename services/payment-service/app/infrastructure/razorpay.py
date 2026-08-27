import hashlib
import hmac

import httpx
from app.domain.providers import ProviderOrder, ProviderRefund


class RazorpayTestAdapter:
    name = "razorpay"

    def __init__(
        self, key_id: str, key_secret: str, webhook_secret: str, base_url: str, test_mode: bool
    ) -> None:
        if not test_mode or not key_id.startswith("rzp_test_"):
            raise ValueError("Only Razorpay test-mode credentials are supported")
        if not key_secret or not webhook_secret:
            raise ValueError("Razorpay secrets are required")
        self._key_id, self._key_secret = key_id, key_secret
        self._webhook_secret, self._base_url = webhook_secret, base_url.rstrip("/")

    async def create_order(
        self, *, amount_paise: int, currency: str, idempotency_key: str
    ) -> ProviderOrder:
        async with httpx.AsyncClient(auth=(self._key_id, self._key_secret), timeout=10) as client:
            response = await client.post(
                f"{self._base_url}/orders",
                json={"amount": amount_paise, "currency": currency, "receipt": idempotency_key},
            )
            response.raise_for_status()
            data = response.json()
        return ProviderOrder(
            str(data["id"]),
            int(data["amount"]),
            str(data["currency"]),
            {
                "key_id": self._key_id,
                "order_id": str(data["id"]),
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
        async with httpx.AsyncClient(auth=(self._key_id, self._key_secret), timeout=10) as client:
            response = await client.post(
                f"{self._base_url}/payments/{provider_payment_id}/refund",
                json={"amount": amount_paise, "notes": {"idempotency_key": idempotency_key}},
            )
            response.raise_for_status()
            data = response.json()
        return ProviderRefund(str(data["id"]), data.get("status") == "processed")
