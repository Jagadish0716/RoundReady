import hashlib
import hmac

from app.domain.providers import ProviderOrder, ProviderRefund


class DevelopmentPaymentProvider:
    """Deterministic local provider; it never contacts a payment network."""

    name = "development"

    def __init__(self, webhook_secret: str) -> None:
        if not webhook_secret:
            raise ValueError("Development webhook secret is required")
        self._webhook_secret = webhook_secret

    async def create_order(
        self, *, amount_paise: int, currency: str, idempotency_key: str
    ) -> ProviderOrder:
        reference = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
        order_id = f"order_dev_{reference}"
        return ProviderOrder(
            order_id,
            amount_paise,
            currency,
            {"order_id": order_id, "amount": amount_paise, "currency": currency},
        )

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        expected = hmac.new(self._webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def refund(
        self, *, provider_payment_id: str, amount_paise: int, idempotency_key: str
    ) -> ProviderRefund:
        reference = hashlib.sha256(idempotency_key.encode()).hexdigest()[:24]
        return ProviderRefund(f"refund_dev_{reference}", True)
