import secrets
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from roundready_common.errors import ServiceError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.domain.providers import PaymentProvider
from app.infrastructure.database import get_db_session
from app.infrastructure.razorpay import RazorpayTestAdapter


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
    user_id: Annotated[str | None, Header(alias="X-Authenticated-User-ID")] = None,
    role: Annotated[str | None, Header(alias="X-Authenticated-Role")] = None,
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
        return Identity(UUID(user_id or ""), Role(role or ""))
    except ValueError as exc:
        raise ServiceError(
            code="invalid_internal_identity",
            message="Authenticated internal identity is invalid",
            status_code=401,
        ) from exc


AuthenticatedIdentity = Annotated[Identity, Depends(get_identity)]


async def require_candidate(identity: AuthenticatedIdentity) -> Identity:
    if identity.role is not Role.CANDIDATE:
        raise ServiceError(
            code="candidate_role_required", message="Candidate role is required", status_code=403
        )
    return identity


async def require_admin(identity: AuthenticatedIdentity) -> Identity:
    if identity.role is not Role.ADMIN:
        raise ServiceError(
            code="admin_role_required", message="Admin role is required", status_code=403
        )
    return identity


CandidateIdentity = Annotated[Identity, Depends(require_candidate)]
AdminIdentity = Annotated[Identity, Depends(require_admin)]


def get_payment_provider(settings: AppSettings) -> PaymentProvider:
    return RazorpayTestAdapter(
        settings.razorpay_key_id.get_secret_value(),
        settings.razorpay_key_secret.get_secret_value(),
        settings.razorpay_webhook_secret.get_secret_value(),
        settings.razorpay_base_url,
        settings.razorpay_test_mode,
    )


Provider = Annotated[PaymentProvider, Depends(get_payment_provider)]
