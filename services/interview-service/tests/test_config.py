from typing import Any

import pytest
from app.config import Settings
from pydantic import ValidationError


def test_development_video_configuration_still_loads() -> None:
    settings = Settings(environment="development", video_provider="development")
    assert settings.video_provider == "development"


def production_values() -> dict[str, Any]:
    return {
        "environment": "production",
        "database_url": (
            "postgresql+asyncpg://interview:LongRandomDatabaseCredential9@db.internal/interview"
        ),
        "rabbitmq_url": "amqps://interview:LongRandomRabbitCredential9@rabbit.internal/roundready",
        "internal_identity_secret": "i" * 40,
        "livekit_url": "wss://roundready.livekit.cloud",
        "livekit_api_key": "configured-livekit-key",
        "livekit_api_secret": "l" * 40,
        "video_provider": "livekit",
        "livekit_test_mode": False,
    }


def test_production_livekit_configuration_loads() -> None:
    settings = Settings(**production_values())
    assert settings.video_provider == "livekit"
    assert settings.livekit_test_mode is False


def test_production_missing_credentials_fails_safely() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production")


@pytest.mark.parametrize(("provider", "test_mode"), [("development", False), ("livekit", True)])
def test_production_rejects_development_or_test_provider(provider: str, test_mode: bool) -> None:
    values = production_values()
    values.update(video_provider=provider, livekit_test_mode=test_mode)
    with pytest.raises(ValidationError):
        Settings(**values)


def test_production_rejects_local_or_insecure_livekit_url() -> None:
    values = production_values()
    values["livekit_url"] = "ws://localhost:7880"
    with pytest.raises(ValidationError):
        Settings(**values)
