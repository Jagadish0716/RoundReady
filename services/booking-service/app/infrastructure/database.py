from collections.abc import AsyncIterator

from app.config import get_settings
from roundready_common.database import create_postgres_engine, managed_session
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

settings = get_settings()
engine = create_postgres_engine(
    settings.database_url,
    pooling=settings.database_pooling,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout_seconds=settings.database_pool_timeout_seconds,
    pool_recycle_seconds=settings.database_pool_recycle_seconds,
    pool_pre_ping=settings.database_pool_pre_ping,
    connect_timeout_seconds=settings.database_connect_timeout_seconds,
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with managed_session(session_factory) as session:
        yield session
