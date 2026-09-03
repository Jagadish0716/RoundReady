from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, Header
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from roundready_common.redis import create_redis_client

from app.config import Settings, get_settings
from app.rate_limit import RateLimiter, RedisRateLimiter


class Role(StrEnum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    role: Role


AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        yield client


HttpClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_rate_limiter(settings: AppSettings) -> RateLimiter:
    return RedisRateLimiter(create_redis_client(settings.redis_url, decode_responses=True))


Limiter = Annotated[RateLimiter, Depends(get_rate_limiter)]


async def authenticate(
    settings: AppSettings,
    client: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    if authorization is None or not authorization.startswith("Bearer "):
        raise ServiceError(code="unauthorized", message="Bearer token required", status_code=401)
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise ServiceError(code="unauthorized", message="Bearer token required", status_code=401)
    try:
        response = await client.get(
            f"{str(settings.auth_service_url).rstrip('/')}/v1/auth/me",
            headers={"Authorization": f"Bearer {token}", "X-Correlation-ID": get_correlation_id()},
        )
    except httpx.HTTPError as exc:
        raise ServiceError(
            code="authentication_service_unavailable",
            message="Authentication service is unavailable",
            status_code=503,
        ) from exc
    if response.status_code in {401, 403}:
        raise ServiceError(
            code="invalid_access_token", message="Access token is invalid", status_code=401
        )
    if response.status_code != 200:
        raise ServiceError(
            code="authentication_service_unavailable",
            message="Authentication service is unavailable",
            status_code=503,
        )
    try:
        body = response.json()
        return Identity(user_id=UUID(str(body["id"])), role=Role(str(body["role"])))
    except (KeyError, TypeError, ValueError) as exc:
        raise ServiceError(
            code="authentication_service_invalid_response",
            message="Authentication service returned an invalid response",
            status_code=503,
        ) from exc


AuthenticatedIdentity = Annotated[Identity, Depends(authenticate)]
