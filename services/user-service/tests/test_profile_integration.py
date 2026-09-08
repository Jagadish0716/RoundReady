import io
import zipfile
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from alembic import command
from alembic.config import Config
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
    assert created.json()["email"] == candidate_headers["X-User-Email"]
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
            "experience_years": 21,
            "linkedin_url": "https://example.com/not-linkedin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_email_cannot_be_overridden(
    client: TestClient, candidate_headers: dict[str, str], profile_payload: dict[str, object]
) -> None:
    response = client.put(
        "/v1/me/profile",
        headers=candidate_headers,
        json={**profile_payload, "email": "attacker@example.com"},
    )
    assert response.status_code == 422


def test_profile_boundaries_and_phone_normalization(
    client: TestClient, profile_payload: dict[str, object]
) -> None:
    for years in (0, 20):
        headers = identity_headers()
        response = client.put(
            "/v1/me/profile",
            headers=headers,
            json={**profile_payload, "experience_years": years, "phone": "+91 98765 43210"},
        )
        assert response.status_code == 200
        assert response.json()["phone"] == "+919876543210"
    for years in (-1, 21):
        assert (
            client.put(
                "/v1/me/profile",
                headers=identity_headers(),
                json={**profile_payload, "experience_years": years},
            ).status_code
            == 422
        )
    assert (
        client.put(
            "/v1/me/profile",
            headers=identity_headers(),
            json={**profile_payload, "preferred_language": "Klingon"},
        ).status_code
        == 422
    )


def _docx() -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return output.getvalue()


def test_private_resume_upload_and_download(
    client: TestClient, candidate_headers: dict[str, str], profile_payload: dict[str, object]
) -> None:
    files = {"resume": ("../../candidate.pdf", b"%PDF-1.4\nbody", "application/pdf")}
    before_profile = client.post("/v1/me/resume", headers=candidate_headers, files=files)
    assert before_profile.status_code == 404
    client.put("/v1/me/profile", headers=candidate_headers, json=profile_payload)
    stored = client.post("/v1/me/resume", headers=candidate_headers, files=files)
    fetched = client.get("/v1/me/resume", headers=candidate_headers)
    assert stored.status_code == 200
    assert stored.json()["file_name"] == "candidate.pdf"
    assert "storage_url" not in stored.json() and "checksum_sha256" not in stored.json()
    assert fetched.json() == stored.json()
    downloaded = client.get("/v1/me/resume/content", headers=candidate_headers)
    assert downloaded.status_code == 200 and downloaded.content == b"%PDF-1.4\nbody"
    assert client.get("/v1/me/resume", headers=identity_headers()).status_code == 404


def test_resume_type_size_and_doc_formats(
    client: TestClient, profile_payload: dict[str, object]
) -> None:
    headers = identity_headers()
    client.put("/v1/me/profile", headers=headers, json=profile_payload)
    invalid = client.post(
        "/v1/me/resume",
        headers=headers,
        files={"resume": ("resume.pdf", b"not pdf", "application/pdf")},
    )
    oversized = client.post(
        "/v1/me/resume",
        headers=headers,
        files={"resume": ("resume.pdf", b"%PDF-" + b"x" * (5 * 1024 * 1024), "application/pdf")},
    )
    assert invalid.status_code == 422
    assert oversized.status_code == 413
    formats = [
        ("resume.doc", bytes.fromhex("D0CF11E0A1B11AE1") + b"doc", "application/msword"),
        (
            "resume.docx",
            _docx(),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    ]
    for name, content, mime in formats:
        assert (
            client.post(
                "/v1/me/resume", headers=headers, files={"resume": (name, content, mime)}
            ).status_code
            == 200
        )


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


def test_constraint_migration_round_trip(client: TestClient) -> None:
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.downgrade(alembic_config, "0001_candidate_profiles")
    command.upgrade(alembic_config, "head")
