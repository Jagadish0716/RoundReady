from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from roundready_common.errors import ServiceError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth_service import AuthenticatedIdentity, AuthService
from app.config import Settings, get_settings
from app.domain.models import Role
from app.infrastructure.database import get_db_session

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def get_auth_service(session: DatabaseSession, settings: AppSettings) -> AuthService:
    return AuthService(session, settings)


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_identity(
    credentials: BearerCredentials, service: AuthServiceDependency
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ServiceError(
            code="authentication_required",
            message="Bearer authentication is required",
            status_code=401,
        )
    return await service.authenticate_access_token(credentials.credentials)


CurrentIdentity = Annotated[AuthenticatedIdentity, Depends(get_current_identity)]


def require_roles(*roles: Role) -> Callable[[CurrentIdentity], Awaitable[AuthenticatedIdentity]]:
    async def dependency(identity: CurrentIdentity) -> AuthenticatedIdentity:
        if identity.credential.role not in roles:
            raise ServiceError(
                code="insufficient_permissions",
                message="The authenticated role cannot perform this action",
                status_code=403,
            )
        return identity

    return dependency


AdminIdentity = Annotated[AuthenticatedIdentity, Depends(require_roles(Role.ADMIN))]
