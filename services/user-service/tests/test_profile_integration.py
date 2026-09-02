from uuid import UUID, uuid4

import psycopg
from conftest import identity_headers
from fastapi.testclient import TestClient


def test_health_and_correlation_id(client: TestClient) -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "user-service-test"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "user-service-test"


def test_internal_identity_is_required(client: TestClient) -> None:
    missing = client.get("/v1/me/profile")
    spoofed = client.get(
        "/v1/me/profile",
        headers={
            "X-User-ID": str(uuid4()),
            "X-User-Role": "candidate",
            "X-Internal-Identity-Secret": "wrong-secret",
        },
    )
    assert missing.status_code == 401
    assert spoofed.status_code == 401
    assert spoofed.json()["error"]["code"] == "invalid_internal_identity"


def test_candidate_creates_gets_and_updates_own_profile(
    client: TestClient, candidate_headers: dict[str, str], profile_payload: dict[str, object]
) -> None:
    absent = client.get("/v1/me/profile", headers=candidate_headers)
    created = client.put("/v1/me/profile", headers=candidate_headers, json=profile_payload)
    fetched = client.get("/v1/me/profile", headers=candidate_headers)
    updated_payload = {**profile_payload, "city": "Hyderabad", "experience_years": "5.0"}
    updated = client.put("/v1/me/profile", headers=candidate_headers, json=updated_payload)

    assert absent.status_code == 404
    assert created.status_code == 200
    assert created.json()["user_id"] == candidate_headers["X-User-ID"]
    assert fetched.json() == created.json()
    assert updated.json()["city"] == "Hyderabad"
    assert updated.json()["experience_years"] == "5.0"
    assert updated.json()["created_at"] == created.json()["created_at"]


def test_user_id_spoofing_is_rejected(
    client: TestClient, candidate_headers: dict[str, str], profile_payload: dict[str, object]
) -> None:
    response = client.put(
        "/v1/me/profile",
        headers=candidate_headers,
        json={**profile_payload, "user_id": str(uuid4())},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_candidate_cannot_access_another_candidate(
    client: TestClient, profile_payload: dict[str, object]
) -> None:
    first = identity_headers()
    second = identity_headers()
    assert client.put("/v1/me/profile", headers=first, json=profile_payload).status_code == 200
    assert client.get("/v1/me/profile", headers=second).status_code == 404
    target_id = first["X-User-ID"]
    forbidden = client.get(f"/v1/admin/candidates/{target_id}", headers=second)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "admin_role_required"


def test_admin_safe_lookup(client: TestClient, profile_payload: dict[str, object]) -> None:
    candidate = identity_headers()
    created = client.put("/v1/me/profile", headers=candidate, json=profile_payload)
    admin = identity_headers(role="admin")
    response = client.get(f"/v1/admin/candidates/{created.json()['user_id']}", headers=admin)
    assert response.status_code == 200
    assert response.json()["user_id"] == created.json()["user_id"]


def test_interviewer_role_cannot_use_candidate_profile_api(
    client: TestClient, profile_payload: dict[str, object]
) -> None:
    response = client.put(
        "/v1/me/profile", headers=identity_headers(role="interviewer"), json=profile_payload
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "candidate_role_required"


def test_profile_validation(client: TestClient, candidate_headers: dict[str, str]) -> None:
    response = client.put(
        "/v1/me/profile",
        headers=candidate_headers,
        json={
            "full_name": " ",
            "phone": "9876543210",
            "experience_years": 61,
            "linkedin_url": "https://example.com/not-linkedin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_resume_metadata_foundation(
    client: TestClient, candidate_headers: dict[str, str], profile_payload: dict[str, object]
) -> None:
    resume = {
        "storage_url": "https://documents.example.in/resumes/candidate.pdf",
        "file_name": "candidate-resume.pdf",
        "content_type": "application/pdf",
        "size_bytes": 204800,
        "checksum_sha256": "a" * 64,
    }
    before_profile = client.put("/v1/me/resume", headers=candidate_headers, json=resume)
    assert before_profile.status_code == 409
    client.put("/v1/me/profile", headers=candidate_headers, json=profile_payload)
    stored = client.put("/v1/me/resume", headers=candidate_headers, json=resume)
    fetched = client.get("/v1/me/resume", headers=candidate_headers)
    assert stored.status_code == 200
    assert stored.json()["checksum_sha256"] == "a" * 64
    assert fetched.json() == stored.json()


def test_schema_contains_only_user_service_data(postgres_url: str) -> None:
    sync_url = postgres_url.replace("postgresql+psycopg", "postgresql")
    with psycopg.connect(sync_url) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        )
        tables = {row[0] for row in cursor.fetchall()}
    assert tables == {"alembic_version", "candidate_profiles", "resume_metadata"}


def test_profile_persists_across_application_restart(
    client: TestClient, profile_payload: dict[str, object]
) -> None:
    headers = identity_headers(user_id=UUID("4bf4d706-1522-4f37-b24e-769668a36dc8"))
    assert client.put("/v1/me/profile", headers=headers, json=profile_payload).status_code == 200

    from app.main import create_app

    with TestClient(create_app()) as restarted_client:
        response = restarted_client.get("/v1/me/profile", headers=headers)
    assert response.status_code == 200
    assert response.json()["full_name"] == profile_payload["full_name"]
