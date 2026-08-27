from uuid import UUID

from app.api.schemas import (
    IdentityResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.dependencies import AdminIdentity, AuthServiceDependency, CurrentIdentity
from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


@router.post("/register", response_model=IdentityResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, service: AuthServiceDependency) -> IdentityResponse:
    credential = await service.register(request)
    return IdentityResponse.model_validate(credential)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, service: AuthServiceDependency) -> TokenResponse:
    return await service.login(request)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, service: AuthServiceDependency) -> TokenResponse:
    return await service.rotate_refresh_token(request.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: LogoutRequest, identity: CurrentIdentity, service: AuthServiceDependency
) -> Response:
    await service.logout(identity, request.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=IdentityResponse)
async def current_identity(identity: CurrentIdentity) -> IdentityResponse:
    return IdentityResponse.model_validate(identity.credential)


@router.post("/users/{user_id}/disable", response_model=IdentityResponse)
async def disable_user(
    user_id: UUID, _admin: AdminIdentity, service: AuthServiceDependency
) -> IdentityResponse:
    credential = await service.disable_user(user_id)
    return IdentityResponse.model_validate(credential)
