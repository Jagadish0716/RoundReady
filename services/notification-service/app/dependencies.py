import secrets
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from roundready_common.errors import ServiceError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.infrastructure.database import get_db_session

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


class Role(StrEnum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    role: Role


async def get_identity(
    settings: AppSettings,
    user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    secret: Annotated[str | None, Header(alias="X-Internal-Identity-Secret")] = None,
) -> Identity:
    expected = settings.internal_service_secret.get_secret_value()
    if not expected or secret is None or not secrets.compare_digest(expected, secret):
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is required",
            status_code=401,
        )
    try:
        identity = Identity(UUID(user_id or ""), Role(role or ""))
    except ValueError as exc:
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is invalid",
            status_code=401,
        ) from exc
    if identity.role not in {Role.CANDIDATE, Role.INTERVIEWER}:
        raise ServiceError(
            code="participant_role_required",
            message="Candidate or interviewer role is required",
            status_code=403,
        )
    return identity


AuthenticatedIdentity = Annotated[Identity, Depends(get_identity)]
