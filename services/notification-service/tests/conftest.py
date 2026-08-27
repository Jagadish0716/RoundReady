import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.domain.providers import ProviderMessage
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.config import testcontainers_config

testcontainers_config.ryuk_disabled = True


class ControlledProvider:
    def __init__(self, channel: str) -> None:
        self.channel = channel
        self.failures_remaining = 0
        self.messages: list[ProviderMessage] = []

    async def send(self, message: ProviderMessage) -> str:
        self.messages.append(message)
        if self.failures_remaining:
            self.failures_remaining -= 1
            raise RuntimeError("simulated provider failure")
        return f"mock-{self.channel}-{len(self.messages)}"


EMAIL = ControlledProvider("email")
WHATSAPP = ControlledProvider("whatsapp")


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest.fixture(scope="session")
def client(postgres_url: str) -> Iterator[TestClient]:
    os.environ.update(
        {
            "NOTIFICATION_DATABASE_URL": postgres_url.replace(
                "postgresql+psycopg", "postgresql+asyncpg"
            ),
            "DATABASE_POOLING": "false",
            "MAX_DELIVERY_ATTEMPTS": "3",
            "RETRY_BASE_SECONDS": "1",
            "RETRY_MAX_SECONDS": "4",
        }
    )
    from app.config import get_settings

    get_settings.cache_clear()
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")
    from app.main import create_app

    with TestClient(create_app()) as value:
        yield value


@pytest.fixture(autouse=True)
def reset_providers() -> None:
    EMAIL.failures_remaining = 0
    EMAIL.messages.clear()
    WHATSAPP.failures_remaining = 0
    WHATSAPP.messages.clear()
