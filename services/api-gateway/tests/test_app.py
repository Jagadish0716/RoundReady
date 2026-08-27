from app.main import app
from fastapi.testclient import TestClient


def test_health_and_correlation_id() -> None:
    response = TestClient(app).get("/health", headers={"X-Correlation-ID": "test-request"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Correlation-ID"] == "test-request"


def test_gateway_requires_authentication() -> None:
    response = TestClient(app).get("/v1/session")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
