from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse
from app.config import Settings
from app.domain.models import (
    Credential,
    OutboxEvent,
    RefreshToken,
    RevokedAccessToken,
)
from app.domain.security import (
    AccessClaims,
    JwtService,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_needs_rehash,
    verify_password,
)
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class AuthenticatedIdentity:
    credential: Credential
    claims: AccessClaims


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings
        self._jwt = JwtService(settings)

    async def register(self, request: RegisterRequest) -> Credential:
        credential = Credential(
            id=uuid4(),
            email=str(request.email).strip().lower(),
            password_hash=hash_password(request.password),
            role=request.role,
        )
        self._session.add(credential)
        self._session.add(
            self._event(
                "auth.UserRegistered.v1",
                {"user_id": str(credential.id), "role": request.role.value},
            )
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise ServiceError(
                code="email_already_registered",
                message="An account with this email already exists",
                status_code=409,
            ) from exc
        await self._session.refresh(credential)
        return credential

    async def login(self, request: LoginRequest) -> TokenResponse:
        credential = await self._credential_by_email(str(request.email).strip().lower())
        if credential is None or not verify_password(credential.password_hash, request.password):
            raise self._invalid_credentials()
        self._ensure_active(credential)
        if password_needs_rehash(credential.password_hash):
            credential.password_hash = hash_password(request.password)
        response, refresh_record = self._new_token_pair(credential, family_id=uuid4())
        self._session.add(refresh_record)
        await self._session.commit()
        return response

    async def rotate_refresh_token(self, raw_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
            .with_for_update()
        )
        current = result.scalar_one_or_none()
        if current is None:
            raise self._invalid_refresh()
        if current.used_at is not None or current.revoked_at is not None:
            await self._revoke_family(current.family_id, now)
            await self._session.commit()
            raise ServiceError(
                code="refresh_token_reuse",
                message="Refresh token reuse detected; the token family has been revoked",
                status_code=401,
            )
        if current.expires_at <= now:
            current.revoked_at = now
            await self._session.commit()
            raise self._invalid_refresh()

        credential = await self._session.get(Credential, current.credential_id)
        if credential is None:
            raise self._invalid_refresh()
        self._ensure_active(credential)

        response, replacement = self._new_token_pair(credential, family_id=current.family_id)
        current.used_at = now
        current.replaced_by_id = replacement.id
        self._session.add(replacement)
        await self._session.commit()
        return response

    async def authenticate_access_token(self, raw_token: str) -> AuthenticatedIdentity:
        from app.domain.security import InvalidTokenError

        try:
            claims = self._jwt.decode_access_token(raw_token)
        except InvalidTokenError as exc:
            raise ServiceError(
                code="invalid_access_token", message="Access token is invalid", status_code=401
            ) from exc
        credential = await self._session.get(Credential, claims.subject_id)
        if credential is None:
            raise ServiceError(
                code="invalid_access_token", message="Access token is invalid", status_code=401
            )
        self._ensure_active(credential)
        revoked = await self._session.get(RevokedAccessToken, claims.jti)
        if revoked is not None:
            raise ServiceError(
                code="access_token_revoked",
                message="Access token has been revoked",
                status_code=401,
            )
        return AuthenticatedIdentity(credential=credential, claims=claims)

    async def logout(self, identity: AuthenticatedIdentity, raw_refresh_token: str) -> None:
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_refresh_token(raw_refresh_token))
            .with_for_update()
        )
        refresh = result.scalar_one_or_none()
        if refresh is not None and refresh.credential_id != identity.credential.id:
            raise self._invalid_refresh()
        if refresh is not None:
            await self._revoke_family(refresh.family_id, now)
        self._session.add(
            RevokedAccessToken(
                jti=identity.claims.jti,
                credential_id=identity.credential.id,
                expires_at=identity.claims.expires_at,
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()

    async def disable_user(self, user_id: UUID) -> Credential:
        credential = await self._session.get(Credential, user_id, with_for_update=True)
        if credential is None:
            raise ServiceError(code="user_not_found", message="User was not found", status_code=404)
        if credential.is_active:
            now = datetime.now(UTC)
            credential.is_active = False
            credential.disabled_at = now
            await self._session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.credential_id == credential.id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            self._session.add(self._event("auth.UserDisabled.v1", {"user_id": str(credential.id)}))
            await self._session.commit()
        return credential

    def _new_token_pair(
        self, credential: Credential, *, family_id: UUID
    ) -> tuple[TokenResponse, RefreshToken]:
        access_token, claims = self._jwt.issue_access_token(credential.id, credential.role)
        refresh_token = generate_refresh_token()
        refresh_expires_at = datetime.now(UTC) + timedelta(
            seconds=self._settings.refresh_token_ttl_seconds
        )
        record = RefreshToken(
            id=uuid4(),
            credential_id=credential.id,
            family_id=family_id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        return (
            TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                access_expires_at=claims.expires_at,
                refresh_expires_at=refresh_expires_at,
            ),
            record,
        )

    async def _credential_by_email(self, email: str) -> Credential | None:
        result = await self._session.execute(select(Credential).where(Credential.email == email))
        return result.scalar_one_or_none()

    async def _revoke_family(self, family_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )

    def _event(self, event_type: str, payload: dict[str, object]) -> OutboxEvent:
        return OutboxEvent(
            event_type=event_type,
            event_version=1,
            correlation_id=get_correlation_id(),
            payload=payload,
        )

    @staticmethod
    def _ensure_active(credential: Credential) -> None:
        if not credential.is_active:
            raise ServiceError(
                code="account_disabled", message="Account is disabled", status_code=403
            )

    @staticmethod
    def _invalid_credentials() -> ServiceError:
        return ServiceError(
            code="invalid_credentials", message="Email or password is incorrect", status_code=401
        )

    @staticmethod
    def _invalid_refresh() -> ServiceError:
        return ServiceError(
            code="invalid_refresh_token", message="Refresh token is invalid", status_code=401
        )
