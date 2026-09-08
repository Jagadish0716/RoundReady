from uuid import UUID

from app.api.schemas import (
    IdentityResponse,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegistrationResponse,
    ResendVerificationRequest,
    TokenResponse,
    VerificationResponse,
    VerifyEmailRequest,
)
from app.dependencies import AdminIdentity, AuthServiceDependency, CurrentIdentity
from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/v1/auth", tags=["authentication"])


@router.post("/register", response_model=RegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest, service: AuthServiceDependency
) -> RegistrationResponse:
    credential = await service.register(request)
    identity = IdentityResponse.from_credential(credential)
    return RegistrationResponse(
        **identity.model_dump(), development_verification_url=service.development_verification_url
    )


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: ResendVerificationRequest, service: AuthServiceDependency
) -> MessageResponse:
    await service.resend_verification(str(request.email), request.next)
    return MessageResponse(
        message=(
            "If the account exists and still requires verification, "
            "a verification email has been sent."
        )
    )


@router.post("/verify-email", response_model=VerificationResponse)
async def verify_email(
    request: VerifyEmailRequest, service: AuthServiceDependency
) -> VerificationResponse:
    result = await service.verify_email(request.token)
    return VerificationResponse(status=result, message="Email verified successfully.")


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
    return IdentityResponse.from_credential(identity.credential)


@router.post("/users/{user_id}/disable", response_model=IdentityResponse)
async def disable_user(
    user_id: UUID, _admin: AdminIdentity, service: AuthServiceDependency
) -> IdentityResponse:
    credential = await service.disable_user(user_id)
    return IdentityResponse.from_credential(credential)
