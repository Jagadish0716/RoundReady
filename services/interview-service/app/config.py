from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "interview-service"
    environment: Environment = "development"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/interviews",
        validation_alias="INTERVIEW_DATABASE_URL",
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.interview.events", validation_alias="INTERVIEW_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    video_provider: Literal["development", "livekit"] = "livekit"
    internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_IDENTITY_SECRET"
    )
    livekit_url: str = "http://localhost:7880"
    livekit_api_key: SecretStr = Field(default=SecretStr(""), validation_alias="LIVEKIT_API_KEY")
    livekit_api_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="LIVEKIT_API_SECRET"
    )
    livekit_test_mode: bool = True
    participant_token_ttl_seconds: int = Field(default=300, ge=60, le=900)
    join_window_before_seconds: int = Field(default=600, ge=0)
    join_window_after_seconds: int = Field(default=1200, ge=0)
    database_pooling: bool = True

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        require_url(
            "INTERVIEW_DATABASE_URL",
            self.database_url,
            schemes={"postgresql+asyncpg"},
            credentials=True,
        )
        require_url("RABBITMQ_URL", self.rabbitmq_url, schemes={"amqp", "amqps"}, credentials=True)
        require_secret("INTERNAL_IDENTITY_SECRET", self.internal_identity_secret)
        require_secret("LIVEKIT_API_KEY", self.livekit_api_key, minimum_length=8)
        require_secret("LIVEKIT_API_SECRET", self.livekit_api_secret)
        require_url("LIVEKIT_URL", self.livekit_url, schemes={"https", "wss"})
        if self.video_provider != "livekit" or self.livekit_test_mode:
            raise ValueError("development/test video providers are unavailable in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
