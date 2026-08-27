from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.config import Settings
from app.domain.models import Role
from app.domain.security import (
    InvalidTokenError,
    JwtService,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from pydantic import SecretStr


def settings(*, jwt_issuer: str = "unit-issuer", access_token_ttl_seconds: int = 900) -> Settings:
    return Settings(
        jwt_signing_key=SecretStr("unit-test-signing-key-longer-than-thirty-two-bytes"),
        jwt_issuer=jwt_issuer,
        jwt_audience="unit-audience",
        access_token_ttl_seconds=access_token_ttl_seconds,
    )


def test_passwords_are_argon2_hashed() -> None:
    encoded = hash_password("CorrectHorseBattery1!")
    assert encoded.startswith("$argon2id$")
    assert "CorrectHorseBattery1!" not in encoded
    assert verify_password(encoded, "CorrectHorseBattery1!")
    assert not verify_password(encoded, "incorrect-password")


def test_refresh_tokens_are_one_way_hashed() -> None:
    assert hash_refresh_token("a-refresh-token") != "a-refresh-token"
    assert len(hash_refresh_token("a-refresh-token")) == 64


def test_jwt_contains_role_and_validates() -> None:
    service = JwtService(settings())
    subject_id = uuid4()
    token, issued = service.issue_access_token(subject_id, Role.INTERVIEWER)
    decoded = service.decode_access_token(token)
    assert decoded.subject_id == subject_id
    assert decoded.role is Role.INTERVIEWER
    assert decoded.jti == issued.jti


def test_expired_jwt_is_rejected() -> None:
    service = JwtService(settings(access_token_ttl_seconds=1))
    token, _ = service.issue_access_token(
        uuid4(), Role.CANDIDATE, now=datetime.now(UTC) - timedelta(seconds=2)
    )
    with pytest.raises(InvalidTokenError):
        service.decode_access_token(token)


def test_wrong_issuer_is_rejected() -> None:
    issuer = JwtService(settings(jwt_issuer="issuer-one"))
    verifier = JwtService(settings(jwt_issuer="issuer-two"))
    token, _ = issuer.issue_access_token(uuid4(), Role.CANDIDATE)
    with pytest.raises(InvalidTokenError):
        verifier.decode_access_token(token)
