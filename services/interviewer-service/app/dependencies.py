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


async def get_identity(
    settings: AppSettings,
    authenticated_user_id: Annotated[str | None, Header(alias="X-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    internal_secret: Annotated[str | None, Header(alias="X-Internal-Identity-Secret")] = None,
) -> Identity:
    expected = settings.internal_identity_secret.get_secret_value()
    if (
        not expected
        or internal_secret is None
        or not secrets.compare_digest(expected, internal_secret)
    ):
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is required",
            status_code=401,
        )
    try:
        return Identity(UUID(authenticated_user_id or ""), Role(role or ""))
    except ValueError as exc:
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is invalid",
            status_code=401,
        ) from exc


AuthenticatedIdentity = Annotated[Identity, Depends(get_identity)]


async def require_interviewer(identity: AuthenticatedIdentity) -> Identity:
    if identity.role is not Role.INTERVIEWER:
        raise ServiceError(
            code="interviewer_role_required",
            message="Interviewer role is required",
            status_code=403,
        )
    return identity


async def require_admin(identity: AuthenticatedIdentity) -> Identity:
    if identity.role is not Role.ADMIN:
        raise ServiceError(
            code="admin_role_required", message="Admin role is required", status_code=403
        )
    return identity


InterviewerIdentity = Annotated[Identity, Depends(require_interviewer)]
AdminIdentity = Annotated[Identity, Depends(require_admin)]
