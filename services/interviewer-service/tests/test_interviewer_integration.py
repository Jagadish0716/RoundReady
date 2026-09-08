from typing import cast
from uuid import UUID, uuid4

import psycopg
from conftest import headers
from fastapi.testclient import TestClient


def create_profile(
    client: TestClient, identity: dict[str, str], profile: dict[str, object]
) -> dict[str, object]:
    response = client.put("/v1/me/profile", headers=identity, json=profile)
    assert response.status_code == 200, response.text
    return cast(dict[str, object], response.json())


def approve_interviewer(
    client: TestClient,
    interviewer: dict[str, str],
    admin: dict[str, str],
    postgres_url: str,
) -> None:
    satisfy_contact_checks(client, interviewer, postgres_url)
    client.post("/v1/me/verification/submit", headers=interviewer)
    response = client.post(
        f"/v1/admin/interviewers/{interviewer['X-User-ID']}/verification/review",
        headers=admin,
        json={
            "action": "verify",
            "checks": {
                "linkedin_reviewed": True,
                "professional_evidence_reviewed": True,
            },
            "screening": {"screening_status": "passed", "overall_result": "passed"},
        },
    )
    assert response.status_code == 200


def satisfy_contact_checks(
    client: TestClient, interviewer: dict[str, str], postgres_url: str
) -> None:
    mobile = client.post(
        "/v1/me/verification/mobile/request",
        headers=interviewer,
        json={"mobile": "+919876543210"},
    ).json()
    client.post(
        "/v1/me/verification/mobile/verify",
        headers=interviewer,
        json={"challenge_id": mobile["challenge_id"], "secret": mobile["development_secret"]},
    )
    company = client.post(
        "/v1/me/verification/company-email/request",
        headers=interviewer,
        json={"company_email": "engineer@company.example"},
    ).json()
    client.post(
        "/v1/me/verification/company-email/verify",
        headers=interviewer,
        json={
            "challenge_id": company["challenge_id"],
            "secret": company["development_secret"],
        },
    )
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "INSERT INTO interviewer_verification_checks "
            "(id, interviewer_id, check_type, passed) VALUES (gen_random_uuid(), %s, "
            "'email_verified', true) ON CONFLICT (interviewer_id, check_type) "
            "DO UPDATE SET passed = true",
            (interviewer["X-User-ID"],),
        )


def test_empty_public_interviewer_collection_returns_ok(client: TestClient) -> None:
    response = client.get("/v1/public/interviewers")
    assert response.status_code == 200
    assert response.json() == []


def test_anonymous_public_discovery_returns_only_verified_safe_data(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    admin = headers("admin")
    verified, pending, under_review, rejected, suspended = (headers() for _ in range(5))
    for identity in (verified, pending, under_review, rejected, suspended):
        create_profile(client, identity, profile)
    approve_interviewer(client, verified, admin, postgres_url)
    satisfy_contact_checks(client, under_review, postgres_url)
    satisfy_contact_checks(client, rejected, postgres_url)
    client.post("/v1/me/verification/submit", headers=under_review)
    client.post("/v1/me/verification/submit", headers=rejected)
    client.post(
        f"/v1/admin/interviewers/{rejected['X-User-ID']}/reject",
        headers=admin,
        json={"reason": "Not approved"},
    )
    approve_interviewer(client, suspended, admin, postgres_url)
    client.post(
        f"/v1/admin/interviewers/{suspended['X-User-ID']}/suspend",
        headers=admin,
        json={"reason": "Suspended"},
    )
    discovered = client.get("/v1/public/interviewers")
    assert discovered.status_code == 200
    ids = {item["interviewer_id"] for item in discovered.json()}
    assert verified["X-User-ID"] in ids
    assert not ids.intersection(
        {
            pending["X-User-ID"],
            under_review["X-User-ID"],
            rejected["X-User-ID"],
            suspended["X-User-ID"],
        }
    )
    public = client.get(f"/v1/public/interviewers/{verified['X-User-ID']}")
    assert public.status_code == 200
    assert public.json()["full_name"] == profile["full_name"]
    assert public.json()["price_paise"] == 20000
    assert public.json()["roundready_verified"] is True
    assert public.json()["interview_languages"] == ["English"]
    assert not {
        "company",
        "linkedin_url",
        "github_url",
        "verification_reason",
        "reviewed_by",
        "email",
        "phone",
        "evidence",
        "reviewer_notes",
    }.intersection(public.json())
    assert client.get(f"/v1/public/interviewers/{pending['X-User-ID']}").status_code == 404
    assert client.get("/v1/me/verification").status_code == 401


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


def test_legacy_incomplete_profile_is_readable_but_cannot_submit_verification(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    interviewer = headers()
    create_profile(client, interviewer, profile)
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "UPDATE interviewer_profiles SET company = NULL WHERE user_id = %s",
            (interviewer["X-User-ID"],),
        )
    readable = client.get("/v1/me/profile", headers=interviewer)
    assert readable.status_code == 200
    assert readable.json()["company"] is None
    submitted = client.post("/v1/me/verification/submit", headers=interviewer)
    assert submitted.status_code == 409
    assert submitted.json()["error"] == {
        "code": "profile_incomplete",
        "message": "Complete all required professional profile fields before verification",
        "details": {"fields": ["company"]},
    }


def test_mobile_and_company_contact_challenges_are_ownership_bound_and_one_time(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    interviewer = headers()
    create_profile(client, interviewer, profile)
    initial = client.get("/v1/me/verification", headers=interviewer).json()
    assert initial["account_email"] == interviewer["X-User-Email"]
    assert initial["account_email_verified"] is False

    invalid = client.post(
        "/v1/me/verification/mobile/request",
        headers=interviewer,
        json={"mobile": "+911234567890"},
    )
    assert invalid.status_code == 422
    mobile = client.post(
        "/v1/me/verification/mobile/request",
        headers=interviewer,
        json={"mobile": "+919876543210"},
    )
    assert mobile.status_code == 200
    mobile_challenge = mobile.json()
    assert mobile_challenge["development_secret"].isdigit()
    assert (
        client.post(
            "/v1/me/verification/mobile/request",
            headers=interviewer,
            json={"mobile": "+919876543210"},
        ).status_code
        == 429
    )
    wrong = client.post(
        "/v1/me/verification/mobile/verify",
        headers=interviewer,
        json={"challenge_id": mobile_challenge["challenge_id"], "secret": "000000"},
    )
    assert wrong.status_code == 422
    verified = client.post(
        "/v1/me/verification/mobile/verify",
        headers=interviewer,
        json={
            "challenge_id": mobile_challenge["challenge_id"],
            "secret": mobile_challenge["development_secret"],
        },
    )
    assert verified.status_code == 200
    assert verified.json()["mobile_verified"] is True
    assert verified.json()["mobile_e164"] == "+919876543210"
    assert (
        client.post(
            "/v1/me/verification/mobile/verify",
            headers=interviewer,
            json={
                "challenge_id": mobile_challenge["challenge_id"],
                "secret": mobile_challenge["development_secret"],
            },
        ).status_code
        == 422
    )

    company = client.post(
        "/v1/me/verification/company-email/request",
        headers=interviewer,
        json={"company_email": "jagadisha@amazon.com"},
    ).json()
    company_verified = client.post(
        "/v1/me/verification/company-email/verify",
        headers=interviewer,
        json={
            "challenge_id": company["challenge_id"],
            "secret": company["development_secret"],
        },
    )
    assert company_verified.status_code == 200
    assert company_verified.json()["company_email_verified"] is True
    changed = client.post(
        "/v1/me/verification/company-email/request",
        headers=interviewer,
        json={"company_email": "jagadisha@microsoft.com"},
    )
    assert changed.status_code == 200
    changed_challenge = changed.json()
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "UPDATE contact_verification_challenges "
            "SET expires_at = now() - interval '1 second' WHERE id = %s",
            (changed_challenge["challenge_id"],),
        )
    expired = client.post(
        "/v1/me/verification/company-email/verify",
        headers=interviewer,
        json={
            "challenge_id": changed_challenge["challenge_id"],
            "secret": changed_challenge["development_secret"],
        },
    )
    assert expired.status_code == 422
    assert expired.json()["error"]["code"] == "verification_challenge_expired"
    refreshed = client.get("/v1/me/verification", headers=interviewer).json()
    assert refreshed["company_email_verified"] is False
    assert refreshed["mobile_verified"] is True
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute(
            "SELECT payload::text FROM outbox_events "
            "WHERE event_type = 'interviewer.contact_verification.changed.v1'"
        )
        payloads = [row[0] for row in cursor.fetchall()]
    assert payloads
    assert not any(
        value in payload
        for payload in payloads
        for value in ["9876543210", "amazon.com", "microsoft.com", "secret", "token"]
    )

    limited = headers()
    create_profile(client, limited, profile)
    limited_challenge = client.post(
        "/v1/me/verification/mobile/request",
        headers=limited,
        json={"mobile": "+919999999999"},
    ).json()
    for _ in range(5):
        assert (
            client.post(
                "/v1/me/verification/mobile/verify",
                headers=limited,
                json={"challenge_id": limited_challenge["challenge_id"], "secret": "000000"},
            ).status_code
            == 422
        )
    exhausted = client.post(
        "/v1/me/verification/mobile/verify",
        headers=limited,
        json={"challenge_id": limited_challenge["challenge_id"], "secret": "000000"},
    )
    assert exhausted.status_code == 429


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
    satisfy_contact_checks(client, interviewer, postgres_url)
    assert (
        client.post("/v1/me/verification/submit", headers=interviewer).json()["verification_status"]
        == "under_review"
    )
    queue = client.get("/v1/admin/verification-queue", headers=admin)
    assert user_id in {item["user_id"] for item in queue.json()}
    approved = client.post(
        f"/v1/admin/interviewers/{user_id}/verification/review",
        headers=admin,
        json={
            "action": "verify",
            "checks": {
                "linkedin_reviewed": True,
                "professional_evidence_reviewed": True,
            },
            "screening": {
                "screening_status": "passed",
                "communication_assessment": "Clear communication",
                "technical_assessment": "Strong technical depth",
                "overall_result": "passed",
            },
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "verified"
    verified = client.get("/v1/admin/interviewers?verification_status=verified", headers=admin)
    assert user_id in {item["user_id"] for item in verified.json()}
    suspended = client.post(
        f"/v1/admin/interviewers/{user_id}/suspend", headers=admin, json={"reason": "Policy review"}
    )
    assert suspended.json()["verification_status"] == "suspended"
    suspended_list = client.get(
        "/v1/admin/interviewers?verification_status=suspended", headers=admin
    )
    assert user_id in {item["user_id"] for item in suspended_list.json()}
    reactivated = client.post(f"/v1/admin/interviewers/{user_id}/reactivate", headers=admin)
    assert reactivated.json()["verification_status"] == "verified"
    with (
        psycopg.connect(postgres_url.replace("postgresql+psycopg", "postgresql")) as connection,
        connection.cursor() as cursor,
    ):
        cursor.execute("SELECT event_type FROM outbox_events")
        events = [row[0] for row in cursor.fetchall()]
    assert "interviewer.verification.approved.v1" in events
    assert "interviewer.InterviewerSuspended.v1" in events


def test_admin_interviewer_discovery_is_role_protected_and_filterable(
    client: TestClient, profile: dict[str, object]
) -> None:
    interviewer = headers()
    admin = headers("admin")
    user_id = create_profile(client, interviewer, profile)["user_id"]

    assert client.get("/v1/admin/interviewers").status_code == 401
    assert client.get("/v1/admin/interviewers", headers=headers("candidate")).status_code == 403
    assert client.get("/v1/admin/interviewers", headers=interviewer).status_code == 403
    pending = client.get("/v1/admin/interviewers?verification_status=pending", headers=admin)
    assert pending.status_code == 200
    assert user_id in {item["user_id"] for item in pending.json()}


def test_rejection_requires_reason_and_valid_transition(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    interviewer, admin = headers(), headers("admin")
    user_id = create_profile(client, interviewer, profile)["user_id"]
    invalid = client.post(f"/v1/admin/interviewers/{user_id}/approve", headers=admin)
    assert invalid.status_code == 409
    satisfy_contact_checks(client, interviewer, postgres_url)
    client.post("/v1/me/verification/submit", headers=interviewer)
    missing = client.post(f"/v1/admin/interviewers/{user_id}/reject", headers=admin, json={})
    assert missing.status_code == 422
    rejected = client.post(
        f"/v1/admin/interviewers/{user_id}/reject",
        headers=admin,
        json={"reason": "Insufficient evidence"},
    )
    assert rejected.json()["verification_status"] == "rejected"


def test_layered_evidence_is_private_and_candidate_trust_is_safe(
    client: TestClient, profile: dict[str, object], postgres_url: str
) -> None:
    interviewer, other, admin = headers(), headers(), headers("admin")
    user_id = create_profile(client, interviewer, profile)["user_id"]
    evidence = client.put(
        "/v1/me/verification/evidence",
        headers=interviewer,
        json={
            "evidence_type": "company_email",
            "value_reference": "engineer@company.example",
        },
    )
    assert evidence.status_code == 200
    assert evidence.json()["evidence"][0]["status"] == "pending"
    assert client.get("/v1/me/verification", headers=other).status_code == 404
    satisfy_contact_checks(client, interviewer, postgres_url)
    client.post("/v1/me/verification/submit", headers=interviewer)
    reviewed = client.post(
        f"/v1/admin/interviewers/{user_id}/verification/review",
        headers=admin,
        json={
            "action": "verify",
            "checks": {
                "linkedin_reviewed": True,
                "professional_evidence_reviewed": True,
            },
            "evidence_statuses": {evidence.json()["evidence"][0]["id"]: "verified"},
            "screening": {"screening_status": "passed", "overall_result": "passed"},
        },
    )
    assert reviewed.status_code == 200
    trust = client.get(f"/v1/{user_id}/trust", headers=headers("candidate"))
    assert trust.status_code == 200
    assert trust.json() == {
        "interviewer_id": user_id,
        "roundready_verified": True,
        "contact_verified": True,
        "professional_experience_reviewed": True,
        "screening_passed": True,
    }
    assert "evidence" not in trust.json() and "reviewer_notes" not in trust.json()


def test_interviewer_cannot_self_approve(client: TestClient, profile: dict[str, object]) -> None:
    interviewer = headers("interviewer")
    user_id = create_profile(client, interviewer, profile)["user_id"]
    client.post("/v1/me/verification/submit", headers=interviewer)
    response = client.post(
        f"/v1/admin/interviewers/{user_id}/verification/review",
        headers=interviewer,
        json={"action": "verify"},
    )
    assert response.status_code == 403
    admin_same_user = client.post(
        f"/v1/admin/interviewers/{user_id}/verification/review",
        headers=headers("admin", UUID(str(user_id))),
        json={"action": "verify"},
    )
    assert admin_same_user.status_code == 403


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
