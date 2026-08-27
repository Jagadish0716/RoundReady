from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "booking-service"
    environment: str = "local"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/bookings",
        validation_alias="BOOKING_DATABASE_URL",
    )
    database_pooling: bool = True
    redis_url: str = Field(default="redis://localhost:6379/2", validation_alias="BOOKING_REDIS_URL")
    internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_IDENTITY_SECRET"
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.booking.events", validation_alias="BOOKING_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    hold_ttl_seconds: int = Field(default=300, ge=1, le=1800)
    session_duration_minutes: int = Field(default=20, ge=15, le=60)
    session_price_paise: int = Field(default=20000, ge=20000, le=20000)


@lru_cache
def get_settings() -> Settings:
    return Settings()
