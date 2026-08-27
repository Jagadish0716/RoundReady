from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "payment-service"
    environment: str = "local"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/payments",
        validation_alias="PAYMENT_DATABASE_URL",
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.payment.events", validation_alias="PAYMENT_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    session_price_paise: int = 20000
    payment_provider: str = "razorpay"
    internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_IDENTITY_SECRET"
    )
    razorpay_key_id: SecretStr = Field(default=SecretStr(""), validation_alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="RAZORPAY_KEY_SECRET"
    )
    razorpay_webhook_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="RAZORPAY_WEBHOOK_SECRET"
    )
    razorpay_base_url: str = "https://api.razorpay.com/v1"
    razorpay_test_mode: bool = True
    database_pooling: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
