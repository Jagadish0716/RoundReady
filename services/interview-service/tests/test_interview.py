from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID, uuid4

import httpx
import jwt
from app.domain.providers import ParticipantAccess, VideoRoom
from app.infrastructure.livekit import LiveKitAdapter
from conftest import create_session, headers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text


def test_health_rubric_and_session_provision(client: TestClient, rubric: dict[str, object]) -> None:
    assert client.get("/health").status_code == 200
    response, candidate, interviewer, _ = create_session(client, str(rubric["id"]))
    assert response.status_code == 201
    body = response.json()
    assert (
        body["status"] == "ready"
        and body["candidate_id"] == str(candidate)
        and body["interviewer_id"] == str(interviewer)
    )


def test_booking_event_is_idempotent(client: TestClient, rubric: dict[str, object]) -> None:
    event, booking = uuid4(), uuid4()
    first, candidate, interviewer, payload = create_session(
        client, str(rubric["id"]), event_id=event, booking_id=booking
    )
    second = client.post("/v1/internal/sessions", headers=headers(), json=payload)
    assert first.json()["id"] == second.json()["id"]


def test_only_assigned_participants_receive_tokens(
    client: TestClient, rubric: dict[str, object]
) -> None:
    response, candidate, interviewer, payload = create_session(client, str(rubric["id"]))
    session_id = response.json()["id"]
    candidate_join = client.post(
        f"/v1/sessions/{session_id}/join", headers=headers("candidate", candidate)
    )
    assert candidate_join.status_code == 200
    assert (
        str(candidate) in candidate_join.json()["token"]
        and f"interview-{payload['booking_id']}" in candidate_join.json()["token"]
        and "secret" not in candidate_join.json()
    )
    assert client.post(
        f"/v1/sessions/{session_id}/join", headers=headers("candidate")
    ).status_code in {403, 404}
    assert (
        client.post(
            f"/v1/sessions/{session_id}/join", headers=headers("interviewer", interviewer)
        ).status_code
        == 200
    )
    assert (
        client.post(f"/v1/sessions/{session_id}/join", headers=headers("interviewer")).status_code
        == 404
    )


def test_participant_session_discovery_rubric_and_interviewer_lifecycle(
    client: TestClient, rubric: dict[str, object]
) -> None:
    response, candidate, interviewer, _ = create_session(client, str(rubric["id"]))
    session_id = response.json()["id"]

    candidate_list = client.get("/v1/sessions", headers=headers("candidate", candidate))
    interviewer_list = client.get("/v1/sessions", headers=headers("interviewer", interviewer))
    unrelated_list = client.get("/v1/sessions", headers=headers("candidate"))
    rubric_response = client.get(
        f"/v1/sessions/{session_id}/rubric", headers=headers("interviewer", interviewer)
    )
    candidate_start = client.post(
        f"/v1/sessions/{session_id}/start", headers=headers("candidate", candidate)
    )
    unrelated_start = client.post(
        f"/v1/sessions/{session_id}/start", headers=headers("interviewer")
    )
    started = client.post(
        f"/v1/sessions/{session_id}/start", headers=headers("interviewer", interviewer)
    )
    completed = client.post(
        f"/v1/sessions/{session_id}/complete", headers=headers("interviewer", interviewer)
    )

    assert candidate_list.status_code == 200 and candidate_list.json()[0]["id"] == session_id
    assert interviewer_list.status_code == 200 and interviewer_list.json()[0]["id"] == session_id
    assert unrelated_list.status_code == 200 and unrelated_list.json() == []
    assert rubric_response.status_code == 200 and rubric_response.json()["id"] == str(rubric["id"])
    assert candidate_start.status_code == 403
    assert unrelated_start.status_code == 404
    assert started.json()["status"] == "in_progress"
    assert completed.json()["status"] == "feedback_pending"
    assert (
        client.post(
            f"/v1/sessions/{session_id}/join", headers=headers("candidate", candidate)
        ).status_code
        == 409
    )


def test_attendance_disconnect_reconnect_and_duplicate(
    client: TestClient, rubric: dict[str, object]
) -> None:
    response, candidate, _, _ = create_session(client, str(rubric["id"]))
    sid = response.json()["id"]
    now = datetime.now(UTC)

    def attendance(event_id: str, event_type: str, when: datetime) -> httpx.Response:
        return cast(
            httpx.Response,
            client.post(
                f"/v1/internal/sessions/{sid}/attendance",
                headers=headers(),
                json={
                    "provider_event_id": event_id,
                    "user_id": str(candidate),
                    "event_type": event_type,
                    "occurred_at": when.isoformat(),
                },
            ),
        )

    assert attendance("join-1-" + sid, "joined", now).status_code == 200
    duplicate = attendance("join-1-" + sid, "joined", now)
    assert duplicate.json()["reconnect_count"] == 0
    attendance("left-1-" + sid, "left", now + timedelta(seconds=10))
    rejoin = attendance("join-2-" + sid, "joined", now + timedelta(seconds=12))
    assert rejoin.json()["reconnect_count"] == 1 and rejoin.json()["total_connected_seconds"] == 10


def completed(client: TestClient, rubric: dict[str, object]) -> tuple[str, UUID, UUID]:
    response, candidate, interviewer, _ = create_session(client, str(rubric["id"]))
    sid = response.json()["id"]
    client.post(
        f"/v1/internal/sessions/{sid}/attendance",
        headers=headers(),
        json={
            "provider_event_id": "start-" + sid,
            "user_id": str(candidate),
            "event_type": "joined",
            "occurred_at": datetime.now(UTC).isoformat(),
        },
    )
    done = client.post(
        f"/v1/admin/sessions/{sid}/transition", headers=headers(), json={"status": "completed"}
    )
    assert done.status_code == 200
    return sid, candidate, interviewer


def feedback_payload() -> dict[str, object]:
    return {
        "criterion_scores": [{"key": "design", "score": 8}, {"key": "communication", "score": 4}],
        "strengths": ["Clear API design"],
        "improvement_areas": ["Discuss failure modes"],
        "summary": "Solid backend fundamentals and communication.",
        "readiness_level": "interview_ready",
    }


def test_feedback_authorization_and_candidate_report(
    client: TestClient, rubric: dict[str, object]
) -> None:
    sid, candidate, interviewer = completed(client, rubric)
    assert (
        client.post(
            f"/v1/sessions/{sid}/feedback", headers=headers("interviewer"), json=feedback_payload()
        ).status_code
        == 403
    )
    report = client.post(
        f"/v1/sessions/{sid}/feedback",
        headers=headers("interviewer", interviewer),
        json=feedback_payload(),
    )
    assert report.status_code == 201 and report.json()["total_score"] == 12
    assert (
        client.get(
            f"/v1/sessions/{sid}/feedback", headers=headers("candidate", candidate)
        ).status_code
        == 200
    )
    assert (
        client.get(f"/v1/sessions/{sid}/feedback", headers=headers("candidate")).status_code == 404
    )


def test_feedback_rejected_before_completion_and_invalid_scores(
    client: TestClient, rubric: dict[str, object]
) -> None:
    response, _, interviewer, _ = create_session(client, str(rubric["id"]))
    sid = response.json()["id"]
    assert (
        client.post(
            f"/v1/sessions/{sid}/feedback",
            headers=headers("interviewer", interviewer),
            json=feedback_payload(),
        ).status_code
        == 409
    )
    sid, _, interviewer = completed(client, rubric)
    payload = feedback_payload()
    criterion_scores = payload["criterion_scores"]
    assert isinstance(criterion_scores, list)
    assert isinstance(criterion_scores[0], dict)
    criterion_scores[0]["score"] = 99
    assert (
        client.post(
            f"/v1/sessions/{sid}/feedback",
            headers=headers("interviewer", interviewer),
            json=payload,
        ).status_code
        == 422
    )


def test_terminal_events_and_invalid_transition(
    client: TestClient, rubric: dict[str, object]
) -> None:
    for status in ("candidate_no_show", "interviewer_no_show", "technical_failure"):
        response, _, _, _ = create_session(client, str(rubric["id"]))
        sid = response.json()["id"]
        result = client.post(
            f"/v1/admin/sessions/{sid}/transition", headers=headers(), json={"status": status}
        )
        assert result.status_code == 200
        assert (
            client.post(
                f"/v1/admin/sessions/{sid}/transition",
                headers=headers(),
                json={"status": "completed"},
            ).status_code
            == 409
        )


def test_persistence_and_published_event_records(
    client: TestClient, rubric: dict[str, object], postgres_url: str
) -> None:
    sid, _, interviewer = completed(client, rubric)
    client.post(
        f"/v1/sessions/{sid}/feedback",
        headers=headers("interviewer", interviewer),
        json=feedback_payload(),
    )
    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        assert (
            connection.scalar(
                text("select count(*) from interview_sessions where id=:id"), {"id": sid}
            )
            == 1
        )
        events = (
            connection.execute(
                text(
                    "select event_type from outbox_events "
                    "where payload->>'session_id'=:id order by occurred_at"
                ),
                {"id": sid},
            )
            .scalars()
            .all()
        )
        assert events == [
            "interview.started.v1",
            "interview.completed.v1",
            "feedback.submitted.v1",
        ]
    engine.dispose()


def test_livekit_tokens_are_short_lived_and_room_scoped() -> None:
    secret = "super-secret-with-at-least-thirty-two-bytes"
    adapter = LiveKitAdapter("ws://localhost:7880", "devkey", secret, 300, True)
    access = adapter.create_participant_token(
        room_reference="room-1", identity="user-1", display_name="candidate"
    )
    claims = jwt.decode(
        access.token,
        secret,
        algorithms=["HS256"],
        audience=None,
        options={"verify_aud": False},
    )
    assert (
        claims["video"]["room"] == "room-1"
        and claims["video"]["roomJoin"] is True
        and claims["exp"] - claims["nbf"] == 300
    )
    assert secret not in access.token


def test_repeated_livekit_tokens_are_fresh_and_have_no_admin_grants() -> None:
    secret = "super-secret-with-at-least-thirty-two-bytes"
    adapter = LiveKitAdapter("wss://roundready.livekit.cloud", "APIlive", secret, 300, False)
    first = adapter.create_participant_token(
        room_reference="room-1", identity="assigned-user", display_name="candidate"
    )
    second = adapter.create_participant_token(
        room_reference="room-1", identity="assigned-user", display_name="candidate"
    )
    claims = jwt.decode(
        second.token,
        secret,
        algorithms=["HS256"],
        audience=None,
        options={"verify_aud": False},
    )
    assert first.token != second.token
    assert claims["sub"] == "assigned-user" and claims["video"]["room"] == "room-1"
    assert claims["exp"] - claims["nbf"] == 300
    assert set(claims["video"]) == {
        "roomJoin",
        "room",
        "canPublish",
        "canSubscribe",
        "canPublishData",
        "canUpdateOwnMetadata",
    }


def test_token_provider_failure_returns_controlled_error(
    client: TestClient, rubric: dict[str, object]
) -> None:
    from app.dependencies import get_video_provider

    class FailingTokenProvider:
        name = "livekit"

        async def create_room(
            self, *, room_name: str, starts_at: datetime, ends_at: datetime
        ) -> VideoRoom:
            return VideoRoom(room_name, "wss://roundready.livekit.cloud")

        def create_participant_token(
            self, *, room_reference: str, identity: str, display_name: str
        ) -> ParticipantAccess:
            raise ValueError("sensitive provider detail")

    response, candidate, _, _ = create_session(client, str(rubric["id"]))
    app = cast(FastAPI, client.app)
    app.dependency_overrides[get_video_provider] = lambda: FailingTokenProvider()
    try:
        result = client.post(
            f"/v1/sessions/{response.json()['id']}/join",
            headers=headers("candidate", candidate),
        )
        assert result.status_code == 503
        assert result.json()["error"]["code"] == "video_provider_unavailable"
        assert "sensitive provider detail" not in result.text
    finally:
        from conftest import FAKE

        app.dependency_overrides[get_video_provider] = lambda: FAKE
