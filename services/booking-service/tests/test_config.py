import pytest
from app.config import Settings
from pydantic import ValidationError


def test_booking_infrastructure_is_explicit_in_production() -> None:
    assert Settings(environment="test").environment == "test"
    with pytest.raises(ValidationError):
        Settings(environment="production")
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://booking:LongRandomDatabaseCredential9@db.internal/booking",
        redis_url="rediss://booking:LongRandomRedisCredential9@redis.internal:6379/2",
        rabbitmq_url="amqps://booking:LongRandomRabbitCredential9@rabbit.internal/roundready",
        internal_identity_secret="i" * 40,
    )
    assert settings.environment == "production"
