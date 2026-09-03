from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr

Environment = Literal["development", "test", "production"]

_INSECURE_VALUES = {
    "change-me",
    "guest",
    "password",
    "replace-me",
    "roundready",
    "roundready-secret",
    "secret",
}


def is_production(environment: Environment) -> bool:
    return environment == "production"


def require_secret(name: str, value: SecretStr, *, minimum_length: int = 32) -> None:
    raw = value.get_secret_value()
    lowered = raw.strip().lower()
    if (
        len(raw) < minimum_length
        or lowered in _INSECURE_VALUES
        or lowered.startswith(("change-me", "replace-me", "replace-with"))
    ):
        raise ValueError(f"{name} must be supplied as a strong secret")


def require_url(
    name: str,
    value: object,
    *,
    schemes: set[str],
    credentials: bool = False,
) -> None:
    raw = str(value)
    parsed = urlsplit(raw)
    if parsed.scheme not in schemes or not parsed.hostname:
        raise ValueError(f"{name} must be a valid configured URL")
    if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError(f"{name} cannot use localhost in production")
    if credentials:
        password = parsed.password or ""
        username = parsed.username
        if username is None or len(password) < 16:
            raise ValueError(f"{name} must include non-development credentials")
        lowered = password.lower()
        if lowered in _INSECURE_VALUES or lowered.startswith(("change-me", "replace-me")):
            raise ValueError(f"{name} must include non-development credentials")
