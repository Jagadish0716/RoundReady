import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from roundready_common.errors import ServiceError
from roundready_common.redis import create_redis_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.infrastructure.database import get_db_session
from app.infrastructure.holds import RedisHoldStore


class Role(StrEnum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    role: Role


DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def identity(
    settings: AppSettings,
    authenticated_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    secret: Annotated[str | None, Header(alias="X-Internal-Identity-Secret")] = None,
) -> Identity:
    expected = settings.internal_identity_secret.get_secret_value()
    if not expected or secret is None or not secrets.compare_digest(expected, secret):
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is required",
            status_code=401,
        )
    try:
        return Identity(UUID(authenticated_id or ""), Role(role or ""))
    except ValueError as exc:
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is invalid",
            status_code=401,
        ) from exc


AuthIdentity = Annotated[Identity, Depends(identity)]


async def candidate(value: AuthIdentity) -> Identity:
    if value.role is not Role.CANDIDATE:
        raise ServiceError(
            code="candidate_role_required", message="Candidate role is required", status_code=403
        )
    return value


async def admin(value: AuthIdentity) -> Identity:
    if value.role is not Role.ADMIN:
        raise ServiceError(
            code="admin_role_required", message="Admin role is required", status_code=403
        )
    return value


CandidateIdentity = Annotated[Identity, Depends(candidate)]
AdminIdentity = Annotated[Identity, Depends(admin)]


async def hold_store(settings: AppSettings) -> AsyncIterator[RedisHoldStore]:
    redis = create_redis_client(settings.redis_url, decode_responses=True)
    try:
        yield RedisHoldStore(redis, settings.hold_ttl_seconds)
    finally:
        await redis.aclose()


HoldStore = Annotated[RedisHoldStore, Depends(hold_store)]
