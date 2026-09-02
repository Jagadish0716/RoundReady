from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "api-gateway"
    environment: str = "local"
    log_level: str = "INFO"
    telemetry_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    auth_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8001")
    user_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8002")
    interviewer_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8003")
    booking_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8004")
    payment_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8005")
    interview_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8006")
    notification_service_url: AnyHttpUrl = AnyHttpUrl("http://localhost:8007")
    internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="INTERNAL_IDENTITY_SECRET"
    )
    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")
    rate_limit_requests: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, ge=1, validation_alias="RATE_LIMIT_WINDOW_SECONDS"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
