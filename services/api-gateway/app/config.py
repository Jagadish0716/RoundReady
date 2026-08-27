from functools import lru_cache

from pydantic import AnyHttpUrl
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
