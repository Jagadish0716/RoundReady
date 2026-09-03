from typing import Annotated

from app.config import get_settings
from app.infrastructure.database import get_db_session
from fastapi import APIRouter, Depends
from roundready_common.errors import ServiceError
from roundready_common.redis import create_redis_client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["platform"])


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def ready(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceError(
            code="service_not_ready", message="Database is unavailable", status_code=503
        ) from exc
    redis = create_redis_client(get_settings().redis_url)
    try:
        await redis.ping()
    except Exception as exc:
        raise ServiceError(
            code="service_not_ready", message="Redis is unavailable", status_code=503
        ) from exc
    finally:
        await redis.aclose()
    return {"status": "ready"}
