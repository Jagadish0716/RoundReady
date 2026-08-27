import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True
SECRET = "interviewer-service-internal-test-secret"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    os.environ.update(
        {
            "INTERVIEWER_DATABASE_URL": postgres_url.replace(
                "postgresql+psycopg", "postgresql+asyncpg"
            ),
            "DATABASE_POOLING": "false",
            "INTERNAL_IDENTITY_SECRET": SECRET,
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


def headers(role: str = "interviewer", user_id: UUID | None = None) -> dict[str, str]:
    return {
        "X-Authenticated-User-ID": str(user_id or uuid4()),
        "X-Authenticated-Role": role,
        "X-Internal-Identity-Secret": SECRET,
    }


@pytest.fixture
def interviewer_headers() -> dict[str, str]:
    return headers()


@pytest.fixture
def profile() -> dict[str, object]:
    return {
        "headline": "Principal Backend Engineer",
        "company": "Example India",
        "job_title": "Principal Engineer",
        "experience_years": "12.5",
        "linkedin_url": "https://linkedin.com/in/interviewer",
        "github_url": "https://github.com/interviewer",
        "bio": "Backend and distributed systems interviewer.",
    }
