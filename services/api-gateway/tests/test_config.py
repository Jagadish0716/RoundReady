import pytest
from app.config import Settings
from pydantic import ValidationError


def test_development_and_test_configuration_load() -> None:
    assert Settings(environment="development").environment == "development"
    assert Settings(environment="test").environment == "test"


def test_production_rejects_defaults_and_accepts_explicit_infrastructure() -> None:
    with pytest.raises(ValidationError, match="localhost"):
        Settings(environment="production")
    settings = Settings(
        environment="production",
        redis_url="rediss://gateway:LongRandomRedisCredential9@redis.internal:6379/0",
        cors_origins=["https://app.roundready.in"],
        auth_service_url="http://auth-service.internal:8000",
        user_service_url="http://user-service.internal:8000",
        interviewer_service_url="http://interviewer-service.internal:8000",
        booking_service_url="http://booking-service.internal:8000",
        payment_service_url="http://payment-service.internal:8000",
        interview_service_url="http://interview-service.internal:8000",
        notification_service_url="http://notification-service.internal:8000",
        internal_identity_secret="i" * 40,
        notification_internal_identity_secret="n" * 40,
    )
    assert settings.environment == "production"


def test_production_cors_requires_explicit_non_local_origins() -> None:
    with pytest.raises(ValidationError, match="explicit"):
        Settings(environment="production", cors_origins=["*"])

    with pytest.raises(ValidationError, match="localhost"):
        Settings(environment="production", cors_origins=["http://localhost:3000"])
