from collections.abc import AsyncIterator

from app.config import get_settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    **({} if settings.database_pooling else {"poolclass": NullPool}),
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
