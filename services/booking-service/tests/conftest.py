import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True
SECRET = "booking-internal-test-secret"


@pytest.fixture(scope="session")
def infrastructure() -> Iterator[tuple[str, str]]:
    with (
        PostgresContainer("postgres:16-alpine", driver="psycopg") as pg,
        RedisContainer("redis:7-alpine") as redis,
    ):
        yield (
            pg.get_connection_url(),
            f"redis://{redis.get_container_host_ip()}:{redis.get_exposed_port(6379)}/0",
        )


@pytest.fixture(scope="session")
def client(infrastructure: tuple[str, str]) -> Iterator[TestClient]:
    pg, redis = infrastructure
    os.environ.update(
        {
            "BOOKING_DATABASE_URL": pg.replace("postgresql+psycopg", "postgresql+asyncpg"),
            "BOOKING_REDIS_URL": redis,
            "DATABASE_POOLING": "false",
            "INTERNAL_IDENTITY_SECRET": SECRET,
            "HOLD_TTL_SECONDS": "2",
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    from app.main import create_app

    with TestClient(create_app()) as value:
        yield value


def headers(role: str = "candidate", user_id: UUID | None = None) -> dict[str, str]:
    return {
        "X-User-ID": str(user_id or uuid4()),
        "X-User-Role": role,
        "X-Internal-Identity-Secret": SECRET,
    }
