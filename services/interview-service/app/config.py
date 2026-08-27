from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "interview-service"
    environment: str = "local"
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
    video_provider: str = "livekit"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
