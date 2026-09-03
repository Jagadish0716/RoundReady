from app.config import get_settings
from fastapi import APIRouter
from roundready_common.errors import ServiceError
from roundready_common.redis import create_redis_client

router = APIRouter(tags=["platform"])


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def ready() -> dict[str, str]:
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
