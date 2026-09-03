from typing import Any

import pytest
from app.config import Settings
from pydantic import ValidationError


def production_values() -> dict[str, Any]:
    return {
        "environment": "production",
        "database_url": (
            "postgresql+asyncpg://notification:LongRandomDatabaseCredential9@db.internal/notification"
        ),
        "rabbitmq_url": (
            "amqps://notification:LongRandomRabbitCredential9@rabbit.internal/roundready"
        ),
        "user_service_url": "http://user-service.internal:8000",
        "internal_service_secret": "s" * 40,
        "email_provider": "resend",
        "resend_api_base_url": "https://api.resend.com",
        "resend_api_key": "r" * 40,
        "email_from_address": "RoundReady <notifications@roundready.example>",
        "whatsapp_provider": "meta",
        "whatsapp_api_base_url": "https://graph.facebook.com/v23.0",
        "whatsapp_access_token": "w" * 40,
        "whatsapp_phone_number_id": "123456789",
        "whatsapp_template_name": "roundready_notification",
        "whatsapp_template_language": "en",
    }


def test_development_notification_configuration_still_loads() -> None:
    settings = Settings(environment="development")
    assert settings.email_provider == settings.whatsapp_provider == "development"


def test_production_notification_configuration_loads() -> None:
    settings = Settings(**production_values())
    assert settings.email_provider == "resend"
    assert settings.whatsapp_provider == "meta"


def test_production_rejects_development_providers() -> None:
    values = production_values()
    values.update(email_provider="development", whatsapp_provider="development")
    with pytest.raises(ValidationError, match="development notification providers"):
        Settings(**values)


@pytest.mark.parametrize(
    "missing",
    [
        "resend_api_key",
        "email_from_address",
        "whatsapp_access_token",
        "whatsapp_phone_number_id",
        "whatsapp_template_name",
    ],
)
def test_production_rejects_missing_provider_configuration(missing: str) -> None:
    values = production_values()
    values[missing] = ""
    with pytest.raises(ValidationError):
        Settings(**values)
