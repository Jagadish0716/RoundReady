import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True

JWT_TEST_KEY = "auth-test-signing-key-with-at-least-thirty-two-bytes"


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    async_url = postgres_url.replace("postgresql+psycopg", "postgresql+asyncpg")
    os.environ.update(
        {
            "AUTH_DATABASE_URL": async_url,
            "JWT_SIGNING_KEY": JWT_TEST_KEY,
            "JWT_ISSUER": "roundready-auth-tests",
            "JWT_AUDIENCE": "roundready-test-api",
            "ACCESS_TOKEN_TTL_SECONDS": "900",
            "REFRESH_TOKEN_TTL_SECONDS": "3600",
            "DATABASE_POOLING": "false",
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    alembic_config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(alembic_config, "head")

    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def register_user(client: TestClient) -> Any:
    counter = 0

    def register(
        *, role: str = "candidate", password: str = "CorrectHorseBattery1!"
    ) -> dict[str, Any]:
        nonlocal counter
        counter += 1
        response = client.post(
            "/v1/auth/register",
            json={
                "email": f"user-{counter}-{os.urandom(4).hex()}@example.in",
                "password": password,
                "role": role,
            },
        )
        assert response.status_code == 201, response.text
        return {**response.json(), "password": password}

    return register
