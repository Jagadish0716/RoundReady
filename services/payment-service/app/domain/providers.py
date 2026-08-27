from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProviderOrder:
    order_id: str
    amount_paise: int
    currency: str
    checkout_data: dict[str, str | int]


@dataclass(frozen=True)
class ProviderRefund:
    refund_id: str
    processed: bool


class PaymentProvider(Protocol):
    name: str

    async def create_order(
        self, *, amount_paise: int, currency: str, idempotency_key: str
    ) -> ProviderOrder: ...
    def verify_webhook(self, body: bytes, signature: str) -> bool: ...
    async def refund(
        self, *, provider_payment_id: str, amount_paise: int, idempotency_key: str
    ) -> ProviderRefund: ...
