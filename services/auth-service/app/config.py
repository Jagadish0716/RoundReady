from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "auth-service"
    environment: str = "local"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/auth",
        validation_alias="AUTH_DATABASE_URL",
    )
    database_pooling: bool = True
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.auth.events", validation_alias="AUTH_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    jwt_issuer: str = "roundready-auth"
    jwt_audience: str = "roundready-api"
    jwt_algorithm: Literal["HS256", "RS256"] = "HS256"
    jwt_signing_key: SecretStr = Field(default=SecretStr(""), validation_alias="JWT_SIGNING_KEY")
    jwt_verification_key: SecretStr = Field(
        default=SecretStr(""), validation_alias="JWT_VERIFICATION_KEY"
    )
    access_token_ttl_seconds: int = Field(default=900, ge=1, le=3600)
    refresh_token_ttl_seconds: int = Field(default=2_592_000, ge=60, le=7_776_000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
