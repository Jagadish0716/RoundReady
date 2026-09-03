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
        database_pool_size=8,
        database_max_overflow=12,
        database_pool_timeout_seconds=20,
        database_pool_recycle_seconds=900,
        database_connect_timeout_seconds=7,
    )
    assert settings.environment == "production"
    assert (
        settings.database_pooling is True
        and settings.database_pool_pre_ping is True
        and settings.database_pool_size == 8
        and settings.database_max_overflow == 12
        and settings.database_pool_timeout_seconds == 20
        and settings.database_pool_recycle_seconds == 900
        and settings.database_connect_timeout_seconds == 7
    )


def test_production_requires_explicit_jwt_issuer_and_audience() -> None:
    with pytest.raises(ValidationError, match="JWT_ISSUER"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://auth:LongRandomDatabaseCredential9@db.internal/auth",
            rabbitmq_url="amqps://auth:LongRandomRabbitCredential9@rabbit.internal/roundready",
            jwt_signing_key="j" * 40,
        )


def test_production_database_url_requires_non_local_credentials() -> None:
    with pytest.raises(ValidationError, match="AUTH_DATABASE_URL"):
        Settings(
            environment="production",
            database_url="postgresql+asyncpg://auth@db.internal/auth",
            rabbitmq_url="amqps://auth:LongRandomRabbitCredential9@rabbit.internal/roundready",
            jwt_signing_key="j" * 40,
            jwt_issuer="roundready.example",
            jwt_audience="roundready-api.example",
        )
