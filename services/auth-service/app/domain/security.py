import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from app.config import Settings
from app.domain.models import Role
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


class InvalidTokenError(Exception):
    pass


@dataclass(frozen=True)
class AccessClaims:
    subject_id: UUID
    role: Role
    jti: UUID
    expires_at: datetime


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class JwtService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue_access_token(
        self, subject_id: UUID, role: Role, *, now: datetime | None = None
    ) -> tuple[str, AccessClaims]:
        issued_at = now or datetime.now(UTC)
        expires_at = issued_at + timedelta(seconds=self._settings.access_token_ttl_seconds)
        claims = AccessClaims(subject_id=subject_id, role=role, jti=uuid4(), expires_at=expires_at)
        payload = {
            "sub": str(subject_id),
            "role": role.value,
            "jti": str(claims.jti),
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": expires_at,
        }
        return jwt.encode(
            payload, self._signing_key(), algorithm=self._settings.jwt_algorithm
        ), claims

    def decode_access_token(self, token: str) -> AccessClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._verification_key(),
                algorithms=[self._settings.jwt_algorithm],
                issuer=self._settings.jwt_issuer,
                audience=self._settings.jwt_audience,
                options={"require": ["sub", "role", "jti", "iss", "aud", "iat", "exp"]},
            )
            return AccessClaims(
                subject_id=UUID(payload["sub"]),
                role=Role(payload["role"]),
                jti=UUID(payload["jti"]),
                expires_at=datetime.fromtimestamp(payload["exp"], UTC),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
            raise InvalidTokenError from exc

    def _signing_key(self) -> str:
        key = self._settings.jwt_signing_key.get_secret_value()
        if self._settings.jwt_algorithm == "HS256" and len(key.encode()) < 32:
            raise RuntimeError("JWT_SIGNING_KEY must contain at least 32 bytes")
        if not key:
            raise RuntimeError("JWT_SIGNING_KEY is required")
        return key

    def _verification_key(self) -> str:
        key = self._settings.jwt_verification_key.get_secret_value()
        return key or self._signing_key()
