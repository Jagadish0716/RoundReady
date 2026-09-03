from typing import Any, cast

import pytest
from roundready_common import database
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool


def test_production_pool_options_and_connect_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    sentinel = cast(AsyncEngine, object())

    def fake_create(url: str, **options: Any) -> AsyncEngine:
        captured.update(url=url, **options)
        return sentinel

    monkeypatch.setattr(database, "create_async_engine", fake_create)
    result = database.create_postgres_engine(
        "postgresql+asyncpg://user:password@db.example/app",
        pooling=True,
        pool_size=8,
        max_overflow=12,
        pool_timeout_seconds=20,
        pool_recycle_seconds=900,
        pool_pre_ping=True,
        connect_timeout_seconds=7,
    )
    assert result is sentinel
    assert captured == {
        "url": "postgresql+asyncpg://user:password@db.example/app",
        "pool_size": 8,
        "max_overflow": 12,
        "pool_timeout": 20,
        "pool_recycle": 900,
        "pool_pre_ping": True,
        "connect_args": {"timeout": 7.0},
    }


def test_testcontainer_mode_uses_null_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_create(_url: str, **options: Any) -> AsyncEngine:
        captured.update(options)
        return cast(AsyncEngine, object())

    monkeypatch.setattr(database, "create_async_engine", fake_create)
    database.create_postgres_engine(
        "postgresql+asyncpg://user:password@localhost/app",
        pooling=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout_seconds=30,
        pool_recycle_seconds=1800,
        pool_pre_ping=True,
        connect_timeout_seconds=10,
    )
    assert captured == {"connect_args": {"timeout": 10.0}, "poolclass": NullPool}


@pytest.mark.asyncio
async def test_managed_session_rolls_back_and_closes_after_failure() -> None:
    class FakeSession:
        rolled_back = False
        closed = False

        async def __aenter__(self) -> "FakeSession":
            return self

        async def __aexit__(self, *_args: object) -> None:
            self.closed = True

        async def rollback(self) -> None:
            self.rolled_back = True

    fake = FakeSession()
    factory = cast(async_sessionmaker[AsyncSession], lambda: fake)
    with pytest.raises(RuntimeError, match="request failed"):
        async with database.managed_session(factory):
            raise RuntimeError("request failed")
    assert fake.rolled_back is True
    assert fake.closed is True
