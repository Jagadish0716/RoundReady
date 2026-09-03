from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import httpx
import pytest
from app.config import Settings, get_settings
from app.dependencies import get_http_client, get_rate_limiter
from app.main import create_app
from fastapi.testclient import TestClient

USER_ID = uuid4()


class FakeLimiter:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[str, int, int]] = []

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        self.calls.append((key, limit, window_seconds))
        return self.allowed


@pytest.fixture
def gateway() -> Iterator[tuple[TestClient, list[httpx.Request], FakeLimiter]]:
    requests: list[httpx.Request] = []
    limiter = FakeLimiter()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/auth/me":
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if token != "valid-token":
                return httpx.Response(401, json={"error": {"code": "invalid_access_token"}})
            return httpx.Response(
                200, json={"id": str(USER_ID), "role": "candidate", "is_active": True}
            )
        return httpx.Response(
            200,
            json={
                "path": request.url.path,
                "user_id": request.headers.get("X-User-ID"),
                "role": request.headers.get("X-User-Role"),
                "correlation": request.headers.get("X-Correlation-ID"),
            },
        )

    async def client_override() -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            yield client

    settings = Settings(
        internal_identity_secret="internal-test-secret",
        notification_internal_identity_secret="notification-test-secret",
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_http_client] = client_override
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    with TestClient(app) as client:
        yield client, requests, limiter


def test_health_and_correlation_id(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    response = client.get("/health", headers={"X-Correlation-ID": "test-request"})
    assert response.status_code == 200 and response.headers["X-Correlation-ID"] == "test-request"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Content-Security-Policy"] == "frame-ancestors 'none'"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"


def test_metrics_endpoint_is_available_and_omits_request_ids(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    client.post(
        "/v1/auth/login", json={"email": "candidate@example.in", "password": "test-password"}
    )
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "roundready_http_requests_total" in response.text
    assert 'route="/{path:path}"' in response.text
    assert "user_id" not in response.text


def test_invalid_correlation_id_is_replaced_and_propagated(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, requests, _ = gateway
    response = client.post(
        "/v1/auth/login",
        headers={"X-Correlation-ID": "invalid value"},
        json={"email": "candidate@example.in", "password": "test-password"},
    )
    assert response.status_code == 200
    correlation_id = response.headers["X-Correlation-ID"]
    assert correlation_id != "invalid value" and len(correlation_id) == 36
    assert requests[-1].headers["X-Correlation-ID"] == correlation_id


def test_auth_rate_limit_returns_429(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, limiter = gateway
    limiter.allowed = False
    response = client.post(
        "/v1/auth/login", json={"email": "user@example.in", "password": "password"}
    )
    assert response.status_code == 429
    assert limiter.calls[-1] == ("auth:v1/auth/login:testclient", 10, 60)


def test_configured_cors_allows_only_explicit_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        cors_origins=["https://app.roundready.in"],
        internal_identity_secret="internal-test-secret",
        notification_internal_identity_secret="notification-test-secret",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: settings)
    with TestClient(create_app()) as client:
        allowed = client.options(
            "/v1/auth/login",
            headers={
                "Origin": "https://app.roundready.in",
                "Access-Control-Request-Method": "POST",
            },
        )
        denied = client.options(
            "/v1/auth/login",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "POST",
            },
        )
    assert allowed.headers["access-control-allow-origin"] == "https://app.roundready.in"
    assert "access-control-allow-origin" not in denied.headers


def test_oversized_request_is_rejected(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    response = client.post(
        "/v1/auth/login",
        content=b"{}",
        headers={"Content-Length": str(1_048_577)},
    )
    assert response.status_code == 413


@pytest.mark.parametrize("token", ["random-string", "not.a.valid.jwt", "expired-token"])
def test_invalid_tokens_fail(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter], token: str
) -> None:
    client, _, _ = gateway
    response = client.get("/v1/users/me/profile", headers={"Authorization": f"Bearer {token}"})
    assert (
        response.status_code == 401 and response.json()["error"]["code"] == "invalid_access_token"
    )


def test_valid_token_routes_and_replaces_spoofed_identity(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, requests, _ = gateway
    response = client.get(
        "/v1/users/me/profile",
        headers={
            "Authorization": "Bearer valid-token",
            "X-User-ID": str(uuid4()),
            "X-User-Role": "admin",
            "X-Internal-Identity-Secret": "attacker",
            "X-Correlation-ID": "gateway-correlation",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "path": "/v1/me/profile",
        "user_id": str(USER_ID),
        "role": "candidate",
        "correlation": "gateway-correlation",
    }
    downstream = requests[-1]
    assert downstream.headers["X-Internal-Identity-Secret"] == "internal-test-secret"


def test_unauthorized_role_is_forbidden(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    response = client.get(
        "/v1/users/admin/candidates/" + str(uuid4()),
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 403


def test_public_login_routes_without_jwt(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    response = client.post(
        "/v1/auth/login", json={"email": "candidate@example.in", "password": "test-password"}
    )
    assert response.status_code == 200 and response.json()["path"] == "/v1/auth/login"


def test_internal_routes_are_not_public(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, _ = gateway
    response = client.post(
        "/v1/booking/internal/slots/generate", headers={"Authorization": "Bearer valid-token"}
    )
    assert response.status_code == 404


def test_notification_routes_require_auth_and_replace_identity(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, requests, _ = gateway
    assert client.get("/v1/notifications/me").status_code == 401
    response = client.get(
        "/v1/notifications/me",
        headers={"Authorization": "Bearer valid-token", "X-User-ID": str(uuid4())},
    )
    assert response.status_code == 200
    assert response.json()["path"] == "/v1/notifications/me"
    assert response.json()["user_id"] == str(USER_ID)
    assert requests[-1].headers["X-Internal-Identity-Secret"] == "notification-test-secret"


def test_rate_limit_returns_429(
    gateway: tuple[TestClient, list[httpx.Request], FakeLimiter],
) -> None:
    client, _, limiter = gateway
    limiter.allowed = False
    response = client.post("/v1/auth/login", json={})
    assert response.status_code == 429 and response.json()["error"]["code"] == "rate_limit_exceeded"


def test_downstream_unavailable_maps_to_503() -> None:
    async def broken_client() -> AsyncIterator[httpx.AsyncClient]:
        async def fail(_request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("offline")

        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            yield client

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        internal_identity_secret="internal-test-secret"
    )
    app.dependency_overrides[get_http_client] = broken_client
    app.dependency_overrides[get_rate_limiter] = lambda: FakeLimiter()
    with TestClient(app) as client:
        response = client.post("/v1/auth/login", json={})
    assert (
        response.status_code == 503
        and response.json()["error"]["code"] == "downstream_service_unavailable"
    )


def test_downstream_5xx_body_is_not_forwarded() -> None:
    async def failing_client() -> AsyncIterator[httpx.AsyncClient]:
        def respond(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="database password=super-secret")

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            yield client

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(
        internal_identity_secret="internal-test-secret"
    )
    app.dependency_overrides[get_http_client] = failing_client
    app.dependency_overrides[get_rate_limiter] = lambda: FakeLimiter()
    with TestClient(app) as client:
        response = client.post(
            "/v1/auth/login", json={"email": "candidate@example.in", "password": "test"}
        )
    assert response.status_code == 502
    assert "super-secret" not in response.text
