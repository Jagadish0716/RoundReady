from typing import Any

import pytest
from app.config import Settings
from pydantic import ValidationError


def test_development_payment_configuration_still_loads() -> None:
    settings = Settings(environment="development", payment_provider="development")
    assert settings.payment_provider == "development"


def production_values() -> dict[str, Any]:
    return {
        "environment": "production",
        "database_url": (
            "postgresql+asyncpg://payment:LongRandomDatabaseCredential9@db.internal/payment"
        ),
        "rabbitmq_url": "amqps://payment:LongRandomRabbitCredential9@rabbit.internal/roundready",
        "internal_identity_secret": "i" * 40,
        "razorpay_key_id": "rzp_live_configured_key",
        "razorpay_key_secret": "k" * 40,
        "razorpay_webhook_secret": "w" * 40,
        "payment_provider": "razorpay",
        "razorpay_test_mode": False,
    }


def test_production_requires_razorpay_credentials() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")


@pytest.mark.parametrize(
    ("provider", "test_mode", "key_id"),
    [("development", False, "rzp_live_configured_key"), ("razorpay", True, "rzp_test_key")],
)
def test_production_rejects_development_or_test_provider_modes(
    provider: str, test_mode: bool, key_id: str
) -> None:
    values = production_values()
    values.update(payment_provider=provider, razorpay_test_mode=test_mode, razorpay_key_id=key_id)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_razorpay_configuration_loads() -> None:
    settings = Settings(**production_values())
    assert settings.environment == "production"
    assert settings.payment_provider == "razorpay"
    assert settings.razorpay_test_mode is False
