from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    service_name: str = "notification-service"
    environment: Environment = "development"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    database_url: str = Field(
        default="postgresql+asyncpg://roundready:roundready@localhost:5432/notifications",
        validation_alias="NOTIFICATION_DATABASE_URL",
    )
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_exchange: str = Field(
        default="roundready.events", validation_alias="RABBITMQ_EXCHANGE"
    )
    rabbitmq_queue: str = Field(
        default="roundready.notification.events", validation_alias="NOTIFICATION_EVENT_QUEUE"
    )
    rabbitmq_dead_letter_exchange: str = Field(
        default="roundready.events.dlx",
        validation_alias="RABBITMQ_DEAD_LETTER_EXCHANGE",
    )
    email_provider: Literal["development", "resend"] = "development"
    whatsapp_provider: Literal["development", "meta"] = "development"
    provider_timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    resend_api_base_url: str = ""
    resend_api_key: SecretStr = SecretStr("")
    email_from_address: str = ""
    whatsapp_api_base_url: str = ""
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    whatsapp_template_name: str = ""
    whatsapp_template_language: str = ""
    user_service_url: str = "http://user-service:8000"
    internal_service_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_SERVICE_SECRET"
    )
    max_delivery_attempts: int = Field(default=5, ge=1, le=20)
    retry_base_seconds: int = Field(default=5, ge=1, le=3600)
    retry_max_seconds: int = Field(default=3600, ge=1, le=86400)
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
            "NOTIFICATION_DATABASE_URL",
            self.database_url,
            schemes={"postgresql+asyncpg"},
            credentials=True,
        )
        require_url("RABBITMQ_URL", self.rabbitmq_url, schemes={"amqp", "amqps"}, credentials=True)
        require_url("USER_SERVICE_URL", self.user_service_url, schemes={"http", "https"})
        require_secret("INTERNAL_SERVICE_SECRET", self.internal_service_secret)
        if self.email_provider != "resend" or self.whatsapp_provider != "meta":
            raise ValueError("development notification providers are unavailable in production")
        require_url("RESEND_API_BASE_URL", self.resend_api_base_url, schemes={"https"})
        require_secret("RESEND_API_KEY", self.resend_api_key)
        if "@" not in self.email_from_address or len(self.email_from_address) > 320:
            raise ValueError("EMAIL_FROM_ADDRESS must be configured")
        require_url("WHATSAPP_API_BASE_URL", self.whatsapp_api_base_url, schemes={"https"})
        require_secret("WHATSAPP_ACCESS_TOKEN", self.whatsapp_access_token)
        for name, value in (
            ("WHATSAPP_PHONE_NUMBER_ID", self.whatsapp_phone_number_id),
            ("WHATSAPP_TEMPLATE_NAME", self.whatsapp_template_name),
            ("WHATSAPP_TEMPLATE_LANGUAGE", self.whatsapp_template_language),
        ):
            if not value.strip():
                raise ValueError(f"{name} must be configured")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
