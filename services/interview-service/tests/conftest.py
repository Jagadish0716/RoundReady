import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from app.domain.providers import ParticipantAccess, VideoRoom
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True
SECRET = "interview-internal-test-secret"


class FakeVideoProvider:
    name = "livekit"

    async def create_room(
        self, *, room_name: str, starts_at: datetime, ends_at: datetime
    ) -> VideoRoom:
        return VideoRoom(room_name, "ws://livekit.test")

    def create_participant_token(
        self, *, room_reference: str, identity: str, display_name: str
    ) -> ParticipantAccess:
        return ParticipantAccess(
            f"token:{room_reference}:{identity}:{display_name}",
            datetime.now(UTC) + timedelta(minutes=5),
            "ws://livekit.test",
        )


FAKE = FakeVideoProvider()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    os.environ.update(
        {
            "INTERVIEW_DATABASE_URL": postgres_url.replace(
                "postgresql+psycopg", "postgresql+asyncpg"
            ),
            "DATABASE_POOLING": "false",
            "INTERNAL_IDENTITY_SECRET": SECRET,
            "LIVEKIT_API_KEY": "devkey",
            "LIVEKIT_API_SECRET": "testsecret",
            "LIVEKIT_TEST_MODE": "true",
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    from app.dependencies import get_video_provider
    from app.main import create_app

    app = create_app()
    app.dependency_overrides[get_video_provider] = lambda: FAKE
    with TestClient(app) as value:
        yield value


def headers(role: str = "admin", user_id: UUID | None = None) -> dict[str, str]:
    return {
        "X-User-ID": str(user_id or uuid4()),
        "X-User-Role": role,
        "X-Internal-Identity-Secret": SECRET,
    }


@pytest.fixture
def rubric(client: TestClient) -> dict[str, object]:
    result = client.post(
        "/v1/admin/rubrics",
        headers=headers(),
        json={
            "domain": "Backend",
            "topic": "Python APIs",
            "experience_level": "mid",
            "version": uuid4().int % 1000000 + 1,
            "criteria": [
                {"key": "design", "label": "System design", "weight": 60, "maximum_score": 10},
                {
                    "key": "communication",
                    "label": "Communication",
                    "weight": 40,
                    "maximum_score": 5,
                },
            ],
        },
    )
    assert result.status_code == 201
    return result.json()


def create_session(
    client: TestClient,
    rubric_id: str,
    candidate: UUID | None = None,
    interviewer: UUID | None = None,
    event_id: UUID | None = None,
    booking_id: UUID | None = None,
):
    candidate = candidate or uuid4()
    interviewer = interviewer or uuid4()
    now = datetime.now(UTC)
    payload = {
        "event_id": str(event_id or uuid4()),
        "booking_id": str(booking_id or uuid4()),
        "candidate_id": str(candidate),
        "interviewer_id": str(interviewer),
        "rubric_id": rubric_id,
        "scheduled_start": (now - timedelta(minutes=1)).isoformat(),
        "scheduled_end": (now + timedelta(minutes=19)).isoformat(),
    }
    return (
        client.post("/v1/internal/sessions", headers=headers(), json=payload),
        candidate,
        interviewer,
        payload,
    )
