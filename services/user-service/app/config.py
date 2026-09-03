from functools import lru_cache

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "user-service"
    environment: Environment = "development"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/users",
        validation_alias="USER_DATABASE_URL",
    )
    database_pooling: bool = True
    internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_IDENTITY_SECRET"
    )
    internal_service_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_SERVICE_SECRET"
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.user.events", validation_alias="USER_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        require_url(
            "USER_DATABASE_URL",
            self.database_url,
            schemes={"postgresql+asyncpg"},
            credentials=True,
        )
        require_url("RABBITMQ_URL", self.rabbitmq_url, schemes={"amqp", "amqps"}, credentials=True)
        require_secret("INTERNAL_IDENTITY_SECRET", self.internal_identity_secret)
        require_secret("INTERNAL_SERVICE_SECRET", self.internal_service_secret)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
