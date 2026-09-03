import pytest
from app.config import Settings
from pydantic import ValidationError


def test_interviewer_service_environment_hardening() -> None:
    assert Settings(environment="development").environment == "development"
    with pytest.raises(ValidationError):
        Settings(environment="production")
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://interviewer:LongRandomDatabaseCredential9@db.internal/interviewer",
        rabbitmq_url="amqps://interviewer:LongRandomRabbitCredential9@rabbit.internal/roundready",
        internal_identity_secret="i" * 40,
    )
    assert settings.environment == "production"
