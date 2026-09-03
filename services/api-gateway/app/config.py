from functools import lru_cache

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from roundready_common.config import Environment, is_production, require_secret, require_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "api-gateway"
    environment: Environment = "development"
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
    notification_internal_identity_secret: SecretStr = Field(
        default=SecretStr(""), validation_alias="NOTIFICATION_INTERNAL_IDENTITY_SECRET"
    )
    cors_origins: list[str] = Field(default_factory=list, validation_alias="CORS_ORIGINS")
    rate_limit_requests: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, ge=1, validation_alias="RATE_LIMIT_WINDOW_SECONDS"
    )

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        require_url("REDIS_URL", self.redis_url, schemes={"redis", "rediss"}, credentials=True)
        for name, value in (
            ("AUTH_SERVICE_URL", self.auth_service_url),
            ("USER_SERVICE_URL", self.user_service_url),
            ("INTERVIEWER_SERVICE_URL", self.interviewer_service_url),
            ("BOOKING_SERVICE_URL", self.booking_service_url),
            ("PAYMENT_SERVICE_URL", self.payment_service_url),
            ("INTERVIEW_SERVICE_URL", self.interview_service_url),
            ("NOTIFICATION_SERVICE_URL", self.notification_service_url),
        ):
            require_url(name, value, schemes={"http", "https"})
        require_secret("INTERNAL_IDENTITY_SECRET", self.internal_identity_secret)
        require_secret(
            "NOTIFICATION_INTERNAL_IDENTITY_SECRET",
            self.notification_internal_identity_secret,
        )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
