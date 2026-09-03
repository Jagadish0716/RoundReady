import pytest
from app.config import Settings
from pydantic import ValidationError


def test_user_service_environment_hardening() -> None:
    assert Settings(environment="test").environment == "test"
    with pytest.raises(ValidationError):
        Settings(environment="production")
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://user:LongRandomDatabaseCredential9@db.internal/user",
        rabbitmq_url="amqps://user:LongRandomRabbitCredential9@rabbit.internal/roundready",
        internal_identity_secret="i" * 40,
        internal_service_secret="s" * 40,
    )
    assert settings.environment == "production"
