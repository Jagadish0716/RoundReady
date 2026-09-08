from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    StringConstraints,
    field_validator,
)

Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=32)]
NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SupportedLanguage(StrEnum):
    ENGLISH = "English"
    HINDI = "Hindi"
    KANNADA = "Kannada"
    TAMIL = "Tamil"
    TELUGU = "Telugu"
    MALAYALAM = "Malayalam"
    MARATHI = "Marathi"
    BENGALI = "Bengali"


class ProfileUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Annotated[NonBlankText, Field(max_length=160)]
    phone: Phone | None = None
    city: Annotated[NonBlankText, Field(max_length=120)] | None = None
    experience_years: Decimal = Field(default=Decimal("0.0"), ge=0, le=20, decimal_places=1)
    current_role: Annotated[NonBlankText, Field(max_length=160)] | None = None
    target_role: Annotated[NonBlankText, Field(max_length=160)] | None = None
    preferred_language: SupportedLanguage = SupportedLanguage.ENGLISH
    linkedin_url: HttpUrl | None = None

    @field_validator("phone")
    @classmethod
    def valid_e164_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        import phonenumbers

        try:
            parsed = phonenumbers.parse(value, None)
        except phonenumbers.NumberParseException as exc:
            raise ValueError("phone must be a valid international number") from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError("phone must be a valid E.164 number")
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    @field_validator("linkedin_url")
    @classmethod
    def require_linkedin_host(cls, value: HttpUrl | None) -> HttpUrl | None:
        host = value.host if value is not None else None
        if host is not None and not (host == "linkedin.com" or host.endswith(".linkedin.com")):
            raise ValueError("linkedin_url must use a linkedin.com host")
        return value


class CandidateProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    full_name: str
    phone: str | None
    email: EmailStr | None
    city: str | None
    experience_years: Decimal
    current_role: str | None
    target_role: str | None
    preferred_language: str
    linkedin_url: str | None
    created_at: datetime
    updated_at: datetime


class ResumeMetadataUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    storage_url: Annotated[str, StringConstraints(pattern=r"^local://[a-f0-9-]+\.(pdf|doc|docx)$")]
    file_name: Annotated[NonBlankText, Field(max_length=255)]
    content_type: Annotated[NonBlankText, Field(max_length=100)]
    size_bytes: int = Field(gt=0, le=5 * 1024 * 1024)
    checksum_sha256: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]

    @field_validator("content_type")
    @classmethod
    def supported_resume_type(cls, value: str) -> str:
        if value not in {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }:
            raise ValueError("unsupported resume content type")
        return value


class ResumeMetadataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    file_name: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    updated_at: datetime


class NotificationDestinationResponse(BaseModel):
    user_id: UUID
    email: EmailStr | None
    phone: str | None
