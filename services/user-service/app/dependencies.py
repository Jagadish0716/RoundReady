import secrets
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from roundready_common.errors import ServiceError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.identity import AuthenticatedRole, InternalIdentity
from app.infrastructure.database import get_db_session

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


async def get_internal_identity(
    settings: AppSettings,
    authenticated_user_id: Annotated[str | None, Header(alias="X-Authenticated-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-Authenticated-Role")] = None,
    internal_secret: Annotated[str | None, Header(alias="X-Internal-Identity-Secret")] = None,
) -> InternalIdentity:
    expected_secret = settings.internal_identity_secret.get_secret_value()
    if (
        not expected_secret
        or internal_secret is None
        or not secrets.compare_digest(internal_secret, expected_secret)
    ):
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is required",
            status_code=401,
        )
    try:
        return InternalIdentity(
            user_id=UUID(authenticated_user_id or ""), role=AuthenticatedRole(role or "")
        )
    except ValueError as exc:
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is invalid",
            status_code=401,
        ) from exc


AuthenticatedIdentity = Annotated[InternalIdentity, Depends(get_internal_identity)]


async def require_candidate(identity: AuthenticatedIdentity) -> InternalIdentity:
    if identity.role is not AuthenticatedRole.CANDIDATE:
        raise ServiceError(
            code="candidate_role_required",
            message="Candidate role is required",
            status_code=403,
        )
    return identity


async def require_admin(identity: AuthenticatedIdentity) -> InternalIdentity:
    if identity.role is not AuthenticatedRole.ADMIN:
        raise ServiceError(
            code="admin_role_required", message="Admin role is required", status_code=403
        )
    return identity


CandidateIdentity = Annotated[InternalIdentity, Depends(require_candidate)]
AdminIdentity = Annotated[InternalIdentity, Depends(require_admin)]
