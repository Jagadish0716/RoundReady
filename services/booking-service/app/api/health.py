from typing import Annotated

from app.infrastructure.database import get_db_session
from fastapi import APIRouter, Depends
from roundready_common.errors import ServiceError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
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
    except SQLAlchemyError as exc:
        raise ServiceError(
            code="service_not_ready", message="Database is unavailable", status_code=503
        ) from exc
    return {"status": "ready"}
