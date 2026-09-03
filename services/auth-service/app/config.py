from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "auth-service"
    environment: Environment = "development"
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

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        require_url(
            "AUTH_DATABASE_URL",
            self.database_url,
            schemes={"postgresql+asyncpg"},
            credentials=True,
        )
        require_url("RABBITMQ_URL", self.rabbitmq_url, schemes={"amqp", "amqps"}, credentials=True)
        require_secret("JWT_SIGNING_KEY", self.jwt_signing_key)
        if self.jwt_algorithm == "RS256":
            require_secret("JWT_VERIFICATION_KEY", self.jwt_verification_key)
            if "BEGIN PRIVATE KEY" not in self.jwt_signing_key.get_secret_value():
                raise ValueError("JWT_SIGNING_KEY must contain an RSA private key")
            if "BEGIN PUBLIC KEY" not in self.jwt_verification_key.get_secret_value():
                raise ValueError("JWT_VERIFICATION_KEY must contain an RSA public key")
        if self.jwt_issuer.strip() in {"", "roundready-auth"}:
            raise ValueError("JWT_ISSUER must be explicitly configured in production")
        if self.jwt_audience.strip() in {"", "roundready-api"}:
            raise ValueError("JWT_AUDIENCE must be explicitly configured in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
