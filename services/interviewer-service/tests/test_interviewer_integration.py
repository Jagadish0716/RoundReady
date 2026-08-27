from typing import cast
from uuid import uuid4

import psycopg
from conftest import headers
from fastapi.testclient import TestClient


def create_profile(
    client: TestClient, identity: dict[str, str], profile: dict[str, object]
) -> dict[str, object]:
    response = client.put("/v1/me/profile", headers=identity, json=profile)
    assert response.status_code == 200, response.text
    return cast(dict[str, object], response.json())


def test_identity_and_role_enforcement(client: TestClient, profile: dict[str, object]) -> None:
    assert client.get("/v1/me/profile").status_code == 401
    assert (
        client.put("/v1/me/profile", headers=headers("candidate"), json=profile).status_code == 403
    )
    spoof = client.put(
        "/v1/me/profile", headers=headers(), json={**profile, "user_id": str(uuid4())}
    )
    assert spoof.status_code == 422


def test_profile_ownership_and_read_only_reliability(
    client: TestClient, profile: dict[str, object]
) -> None:
    first, second = headers(), headers()
    created = create_profile(client, first, profile)
    assert created["verification_status"] == "pending"
    assert created["reliability_score"] == "100.00"
    assert client.get("/v1/me/profile", headers=second).status_code == 404
    tamper = client.put("/v1/me/profile", headers=first, json={**profile, "reliability_score": 0})
    assert tamper.status_code == 422


def test_skills_are_owned_and_replaceable(
    client: TestClient, interviewer_headers: dict[str, str], profile: dict[str, object]
) -> None:
    create_profile(client, interviewer_headers, profile)
    payload = {
        "skills": [
            {
                "domain": "Backend",
                "topic": "Distributed Systems",
                "skill_name": "Python",
                "experience_years": "10.0",
            },
            {
                "domain": "AWS",
                "topic": "Architecture",
                "skill_name": "ECS",
                "experience_years": "6.0",
            },
        ]
    }
    response = client.put("/v1/me/skills", headers=interviewer_headers, json=payload)
    assert response.status_code == 200
    assert {item["domain"] for item in response.json()} == {"Backend", "AWS"}


def test_verification_approve_suspend_reactivate_and_events(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    interviewer, admin = headers(), headers("admin")
    created = create_profile(client, interviewer, profile)
    user_id = created["user_id"]
    assert (
        client.post("/v1/me/verification/submit", headers=interviewer).json()["verification_status"]
        == "under_review"
    )
    queue = client.get("/v1/admin/verification-queue", headers=admin)
    assert user_id in {item["user_id"] for item in queue.json()}
    approved = client.post(f"/v1/admin/interviewers/{user_id}/approve", headers=admin)
    assert approved.json()["verification_status"] == "verified"
    suspended = client.post(
        f"/v1/admin/interviewers/{user_id}/suspend", headers=admin, json={"reason": "Policy review"}
    )
    assert suspended.json()["verification_status"] == "suspended"
    reactivated = client.post(f"/v1/admin/interviewers/{user_id}/reactivate", headers=admin)
    assert reactivated.json()["verification_status"] == "verified"
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT event_type FROM outbox_events WHERE payload->>'user_id' = %s", (user_id,)
        )
        events = [row[0] for row in cursor.fetchall()]
    assert events.count("interviewer.InterviewerVerified.v1") == 2
    assert "interviewer.InterviewerSuspended.v1" in events


def test_rejection_requires_reason_and_valid_transition(
    client: TestClient, profile: dict[str, object]
) -> None:
    interviewer, admin = headers(), headers("admin")
    user_id = create_profile(client, interviewer, profile)["user_id"]
    invalid = client.post(f"/v1/admin/interviewers/{user_id}/approve", headers=admin)
    assert invalid.status_code == 409
    client.post("/v1/me/verification/submit", headers=interviewer)
    missing = client.post(f"/v1/admin/interviewers/{user_id}/reject", headers=admin, json={})
    assert missing.status_code == 422
    rejected = client.post(
        f"/v1/admin/interviewers/{user_id}/reject",
        headers=admin,
        json={"reason": "Insufficient evidence"},
    )
    assert rejected.json()["verification_status"] == "rejected"


def test_weekly_availability_and_blockouts_publish_changes(
    client: TestClient,
    interviewer_headers: dict[str, str],
    profile: dict[str, object],
    postgres_url: str,
) -> None:
    user_id = create_profile(client, interviewer_headers, profile)["user_id"]
    weekly = client.put(
        "/v1/me/availability/weekly",
        headers=interviewer_headers,
        json={
            "rules": [
                {
                    "weekday": 1,
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "timezone": "Asia/Kolkata",
                }
            ]
        },
    )
    assert weekly.status_code == 200
    blockout = client.post(
        "/v1/me/availability/blockouts",
        headers=interviewer_headers,
        json={
            "starts_at": "2026-09-01T10:00:00Z",
            "ends_at": "2026-09-01T11:00:00Z",
            "reason": "Unavailable",
        },
    )
    assert blockout.status_code == 201
    other = headers()
    assert (
        client.delete(
            f"/v1/me/availability/blockouts/{blockout.json()['id']}", headers=other
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/v1/me/availability/blockouts/{blockout.json()['id']}", headers=interviewer_headers
        ).status_code
        == 204
    )
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT count(*) FROM outbox_events "
            "WHERE event_type = 'interviewer.AvailabilityChanged.v1' "
            "AND payload->>'user_id' = %s",
            (user_id,),
        )
        count = cursor.fetchone()
        assert count is not None
        assert count[0] == 3


def test_no_booking_or_auth_tables(client: TestClient, postgres_url: str) -> None:
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = {row[0] for row in cursor.fetchall()}
    assert "bookings" not in tables and "credentials" not in tables
    assert {
        "interviewer_profiles",
        "interviewer_skills",
        "weekly_availability_rules",
        "availability_blockouts",
    } <= tables
