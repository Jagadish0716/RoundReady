from functools import lru_cache
from urllib.parse import urlsplit

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
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")
    hsts_enabled: bool = Field(default=False, validation_alias="HSTS_ENABLED")
    max_request_body_bytes: int = Field(
        default=1_048_576, ge=1_024, le=10_485_760, validation_alias="MAX_REQUEST_BODY_BYTES"
    )
    rate_limit_requests: int = Field(default=60, ge=1, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window_seconds: int = Field(
        default=60, ge=1, validation_alias="RATE_LIMIT_WINDOW_SECONDS"
    )
    auth_rate_limit_requests: int = Field(
        default=10, ge=1, validation_alias="AUTH_RATE_LIMIT_REQUESTS"
    )
    auth_rate_limit_window_seconds: int = Field(
        default=60, ge=1, validation_alias="AUTH_RATE_LIMIT_WINDOW_SECONDS"
    )

    @model_validator(mode="after")
    def production_configuration(self) -> "Settings":
        if not is_production(self.environment):
            return self
        if not self.cors_origins or "*" in self.cors_origins:
            raise ValueError(
                "CORS_ORIGINS must contain explicit origins and cannot use localhost in production"
            )
        for origin in self.cors_origins:
            parsed_origin = urlsplit(origin)
            if parsed_origin.hostname in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("CORS_ORIGINS cannot use localhost in production")
            if parsed_origin.path not in {"", "/"} or parsed_origin.query or parsed_origin.fragment:
                raise ValueError("CORS_ORIGINS must contain origin values without paths")
            require_url("CORS_ORIGINS", origin, schemes={"https"})
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
