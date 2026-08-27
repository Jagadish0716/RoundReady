from typing import Any, cast
from uuid import uuid4

import psycopg
import pytest
from app.domain.security import hash_password
from fastapi.testclient import TestClient


def login(client: TestClient, user: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        "/v1/auth/login", json={"email": user["email"], "password": user["password"]}
    )
    assert response.status_code == 200, response.text
    return cast(dict[str, Any], response.json())


def test_health_and_application_startup(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "auth-integration-test"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "auth-integration-test"


def test_readiness_maps_low_level_database_failure(client: TestClient) -> None:
    from app.infrastructure.database import get_db_session
    from fastapi import FastAPI

    class UnavailableSession:
        async def execute(self, _statement: object) -> None:
            raise OSError("database unavailable")

    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_db_session] = lambda: UnavailableSession()
    try:
        response = client.get("/ready", headers={"X-Correlation-ID": "readiness-failure"})
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_not_ready",
            "message": "Database is unavailable",
            "details": None,
        },
        "correlation_id": "readiness-failure",
    }


def test_registration_and_user_registered_event(
    client: TestClient, register_user: Any, postgres_url: str
) -> None:
    user = register_user(role="interviewer")
    assert user["role"] == "interviewer"
    assert user["is_active"] is True
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT password_hash FROM credentials WHERE id = %s", (user["id"],))
        password_row = cursor.fetchone()
        assert password_row is not None
        password_hash = password_row[0]
        cursor.execute(
            "SELECT event_type, event_version FROM outbox_events WHERE payload->>'user_id' = %s",
            (user["id"],),
        )
        event = cursor.fetchone()
    assert user["password"] not in password_hash
    assert event == ("auth.UserRegistered.v1", 1)


def test_duplicate_registration(client: TestClient) -> None:
    payload = {
        "email": f"duplicate-{uuid4()}@example.in",
        "password": "CorrectHorseBattery1!",
        "role": "candidate",
    }
    assert client.post("/v1/auth/register", json=payload).status_code == 201
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_registered"


def test_registration_input_validation(client: TestClient) -> None:
    invalid_email = client.post(
        "/v1/auth/register",
        json={"email": "not-an-email", "password": "CorrectHorseBattery1!", "role": "candidate"},
    )
    short_password = client.post(
        "/v1/auth/register",
        json={"email": "valid@example.in", "password": "short", "role": "candidate"},
    )
    public_admin = client.post(
        "/v1/auth/register",
        json={
            "email": "admin-public@example.in",
            "password": "CorrectHorseBattery1!",
            "role": "admin",
        },
    )
    assert invalid_email.status_code == 422
    assert short_password.status_code == 422
    assert public_admin.status_code == 422


def test_login_success_failure_role_claim_and_current_identity(
    client: TestClient, register_user: Any
) -> None:
    user = register_user(role="interviewer")
    tokens = login(client, user)
    me = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    failed = client.post(
        "/v1/auth/login", json={"email": user["email"], "password": "wrong-password"}
    )
    assert me.status_code == 200
    assert me.json()["id"] == user["id"]
    assert me.json()["role"] == "interviewer"
    assert failed.status_code == 401
    assert failed.json()["error"]["code"] == "invalid_credentials"
    assert failed.headers["WWW-Authenticate"] == "Bearer"


def test_refresh_rotation_and_reuse_revokes_family(client: TestClient, register_user: Any) -> None:
    tokens = login(client, register_user())
    rotated = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != tokens["refresh_token"]

    reuse = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reuse.status_code == 401
    assert reuse.json()["error"]["code"] == "refresh_token_reuse"

    family_revoked = client.post(
        "/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )
    assert family_revoked.status_code == 401


def test_logout_revokes_access_and_refresh_tokens(client: TestClient, register_user: Any) -> None:
    tokens = login(client, register_user())
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout = client.post(
        "/v1/auth/logout", headers=headers, json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout.status_code == 204
    assert client.get("/v1/auth/me", headers=headers).status_code == 401
    assert (
        client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code
        == 401
    )


def test_disabled_user_is_denied_and_event_is_recorded(
    client: TestClient, register_user: Any, postgres_url: str
) -> None:
    user = register_user()
    user_tokens = login(client, user)
    admin_id = uuid4()
    admin_email = f"admin-{admin_id}@example.in"
    admin_password = "AdminCorrectHorse1!"
    sync_url = postgres_url.replace("postgresql+psycopg", "postgresql")
    with psycopg.connect(sync_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO credentials (id, email, password_hash, role, is_active, created_at) "
            "VALUES (%s, %s, %s, 'admin', true, now())",
            (admin_id, admin_email, hash_password(admin_password)),
        )
    admin_tokens = login(
        client, {"email": admin_email, "password": admin_password, "id": str(admin_id)}
    )
    disabled = client.post(
        f"/v1/auth/users/{user['id']}/disable",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
    )
    assert disabled.status_code == 200
    user_headers = {"Authorization": f"Bearer {user_tokens['access_token']}"}
    assert client.get("/v1/auth/me", headers=user_headers).status_code == 403
    assert (
        client.post(
            "/v1/auth/login", json={"email": user["email"], "password": user["password"]}
        ).status_code
        == 403
    )
    with psycopg.connect(sync_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM outbox_events "
            "WHERE event_type = 'auth.UserDisabled.v1' AND payload->>'user_id' = %s",
            (user["id"],),
        )
        event_count = cursor.fetchone()
        assert event_count is not None
        assert event_count[0] == 1


def test_non_admin_cannot_disable_user(client: TestClient, register_user: Any) -> None:
    actor = register_user()
    target = register_user()
    tokens = login(client, actor)
    response = client.post(
        f"/v1/auth/users/{target['id']}/disable",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "insufficient_permissions"


def test_persistence_across_application_restart(client: TestClient, register_user: Any) -> None:
    user = register_user()
    first_login = login(client, user)
    assert first_login["access_token"]

    from app.main import create_app

    with TestClient(create_app()) as restarted_client:
        second_login = login(restarted_client, user)
    assert second_login["access_token"]


@pytest.mark.asyncio
async def test_rabbitmq_failure_keeps_outbox_event_for_retry(
    client: TestClient, register_user: Any
) -> None:
    from app.application.outbox import publish_pending_events
    from app.domain.models import OutboxEvent
    from app.infrastructure.database import session_factory
    from sqlalchemy import select

    class UnavailablePublisher:
        async def publish(self, _event: object) -> None:
            raise ConnectionError("RabbitMQ unavailable")

    register_user()
    async with session_factory() as session:
        published = await publish_pending_events(session, cast(Any, UnavailablePublisher()))
        failed = await session.scalar(
            select(OutboxEvent)
            .where(OutboxEvent.published_at.is_(None), OutboxEvent.last_error.is_not(None))
            .order_by(OutboxEvent.occurred_at)
        )

    assert published == 0
    assert failed is not None
    assert failed.publish_attempts >= 1
    assert failed.last_error == "ConnectionError"
