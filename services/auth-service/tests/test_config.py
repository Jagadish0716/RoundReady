import pytest
from app.config import Settings
from pydantic import ValidationError


def test_development_and_test_load_without_production_secrets() -> None:
    assert Settings(environment="development").environment == "development"
    assert Settings(environment="test").environment == "test"


@pytest.mark.parametrize("key", ["", "short", "replace-with-at-least-32-random-bytes"])
def test_production_rejects_missing_or_insecure_jwt_key(key: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://auth:LongRandomDatabaseCredential9@db.internal/auth",
            rabbitmq_url="amqps://auth:LongRandomRabbitCredential9@rabbit.internal/roundready",
            jwt_signing_key=key,
        )


def test_explicit_production_jwt_and_infrastructure_load() -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+asyncpg://auth:LongRandomDatabaseCredential9@db.internal/auth",
        rabbitmq_url="amqps://auth:LongRandomRabbitCredential9@rabbit.internal/roundready",
        jwt_signing_key="j" * 40,
        jwt_issuer="roundready.example",
        jwt_audience="roundready-api.example",
    )
    assert settings.environment == "production"


def test_production_requires_explicit_jwt_issuer_and_audience() -> None:
    with pytest.raises(ValidationError, match="JWT_ISSUER"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://auth:LongRandomDatabaseCredential9@db.internal/auth",
            rabbitmq_url="amqps://auth:LongRandomRabbitCredential9@rabbit.internal/roundready",
            jwt_signing_key="j" * 40,
        )
