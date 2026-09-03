from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


def create_postgres_engine(
    database_url: str,
    *,
    pooling: bool,
    pool_size: int,
    max_overflow: int,
    pool_timeout_seconds: int,
    pool_recycle_seconds: int,
    pool_pre_ping: bool,
    connect_timeout_seconds: int,
) -> AsyncEngine:
    options: dict[str, Any] = {
        "connect_args": {"timeout": float(connect_timeout_seconds)},
    }
    if pooling:
        options.update(
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout_seconds,
            pool_recycle=pool_recycle_seconds,
            pool_pre_ping=pool_pre_ping,
        )
    else:
        options["poolclass"] = NullPool
    return create_async_engine(database_url, **options)


@asynccontextmanager
async def managed_session(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
