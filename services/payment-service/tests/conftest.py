import hashlib
import hmac
import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.domain.providers import ProviderOrder, ProviderRefund
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True
INTERNAL_SECRET = "payment-internal-test-secret"
WEBHOOK_SECRET = "payment-webhook-test-secret"
os.environ.update(
    {
        "INTERNAL_IDENTITY_SECRET": INTERNAL_SECRET,
        "RAZORPAY_KEY_ID": "rzp_test_roundready",
        "RAZORPAY_KEY_SECRET": "test-key-secret",
        "RAZORPAY_WEBHOOK_SECRET": WEBHOOK_SECRET,
        "DATABASE_POOLING": "false",
    }
)


class FakeProvider:
    name = "razorpay"

    def verify_webhook(self, body: bytes, signature: str) -> bool:
        expected = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    async def create_order(
        self, *, amount_paise: int, currency: str, idempotency_key: str
    ) -> ProviderOrder:
        order_id = f"order_{idempotency_key}"
        return ProviderOrder(
            order_id,
            amount_paise,
            currency,
            {
                "key_id": "rzp_test_roundready",
                "order_id": order_id,
                "amount": amount_paise,
                "currency": currency,
            },
        )

    async def refund(
        self, *, provider_payment_id: str, amount_paise: int, idempotency_key: str
    ) -> ProviderRefund:
        return ProviderRefund(f"refund_{idempotency_key}", True)


FAKE_PROVIDER = FakeProvider()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    os.environ["PAYMENT_DATABASE_URL"] = postgres_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    from app.dependencies import get_payment_provider
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_payment_provider] = lambda: FAKE_PROVIDER
    with TestClient(app) as value:
        yield value


def identity(role: str = "candidate", user_id: UUID | None = None) -> dict[str, str]:
    return {
        "X-User-ID": str(user_id or uuid4()),
        "X-User-Role": role,
        "X-Internal-Identity-Secret": INTERNAL_SECRET,
    }


def signature(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
