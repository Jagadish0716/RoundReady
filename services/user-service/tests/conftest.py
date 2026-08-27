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
INTERNAL_TEST_SECRET = "user-service-internal-test-secret"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    os.environ.update(
        {
            "USER_DATABASE_URL": postgres_url.replace("postgresql+psycopg", "postgresql+asyncpg"),
            "DATABASE_POOLING": "false",
            "INTERNAL_IDENTITY_SECRET": INTERNAL_TEST_SECRET,
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


def identity_headers(role: str = "candidate", user_id: UUID | None = None) -> dict[str, str]:
    return {
        "X-Authenticated-User-ID": str(user_id or uuid4()),
        "X-Authenticated-Role": role,
        "X-Internal-Identity-Secret": INTERNAL_TEST_SECRET,
    }


@pytest.fixture
def candidate_headers() -> dict[str, str]:
    return identity_headers()


@pytest.fixture
def profile_payload() -> dict[str, object]:
    return {
        "full_name": "Asha Rao",
        "phone": "+919876543210",
        "email": "asha.rao@example.in",
        "city": "Bengaluru",
        "experience_years": "4.5",
        "current_role": "Software Engineer",
        "target_role": "Senior Backend Engineer",
        "preferred_language": "English",
        "linkedin_url": "https://www.linkedin.com/in/asha-rao",
        "resume_url": "https://documents.example.in/resumes/asha.pdf",
    }
