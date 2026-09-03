from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "payment-service"
    environment: Environment = "development"
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
    payment_provider: Literal["development", "razorpay"] = "razorpay"
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
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86400)
    database_pool_pre_ping: bool = True
    database_connect_timeout_seconds: int = Field(default=10, ge=1, le=60)

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        require_url(
            "PAYMENT_DATABASE_URL",
            self.database_url,
            schemes={"postgresql+asyncpg"},
            credentials=True,
        )
        require_url("RABBITMQ_URL", self.rabbitmq_url, schemes={"amqp", "amqps"}, credentials=True)
        require_secret("INTERNAL_IDENTITY_SECRET", self.internal_identity_secret)
        require_secret("RAZORPAY_KEY_ID", self.razorpay_key_id, minimum_length=12)
        require_secret("RAZORPAY_KEY_SECRET", self.razorpay_key_secret)
        require_secret("RAZORPAY_WEBHOOK_SECRET", self.razorpay_webhook_secret)
        require_url("RAZORPAY_BASE_URL", self.razorpay_base_url, schemes={"https"})
        if self.payment_provider != "razorpay" or self.razorpay_test_mode:
            raise ValueError("development/test payment providers are unavailable in production")
        if not self.razorpay_key_id.get_secret_value().startswith("rzp_live_"):
            raise ValueError("RAZORPAY_KEY_ID must be a live-mode key in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
