from datetime import datetime
from typing import Annotated
from uuid import UUID

from app.domain.models import Role
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

Password = Annotated[str, Field(min_length=12, max_length=128)]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    role: Role
    next: Annotated[str | None, Field(max_length=2048)] = None

    @field_validator("role")
    @classmethod
    def disallow_public_admin_registration(cls, value: Role) -> Role:
        if value is Role.ADMIN:
            raise ValueError("admin accounts cannot be publicly registered")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class ResendVerificationRequest(BaseModel):
    email: EmailStr
    next: Annotated[str | None, Field(max_length=2048)] = None


class VerifyEmailRequest(BaseModel):
    token: Annotated[str, Field(min_length=32, max_length=512)]


class MessageResponse(BaseModel):
    message: str


class VerificationResponse(BaseModel):
    status: str
    message: str


class RefreshRequest(BaseModel):
    refresh_token: Annotated[str, Field(min_length=32, max_length=512)]


class LogoutRequest(RefreshRequest):
    pass


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    role: Role
    is_active: bool
    created_at: datetime
    email_verified_at: datetime | None
    email_verified: bool

    @classmethod
    def from_credential(cls, credential: object) -> "IdentityResponse":
        data = cls.model_validate(credential, from_attributes=True)
        return data.model_copy(update={"email_verified": data.email_verified_at is not None})


class RegistrationResponse(IdentityResponse):
    development_verification_url: str | None = None
