from collections.abc import Awaitable
from typing import Any, Protocol, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError
from roundready_common.errors import ServiceError


class RateLimiter(Protocol):
    async def allow(self, key: str, limit: int, window_seconds: int) -> bool: ...


class RedisRateLimiter:
    _SCRIPT = """
    local current = redis.call('INCR', KEYS[1])
    if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    return current <= tonumber(ARGV[2])
    """

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        try:
            result = await cast(
                Awaitable[Any],
                self._redis.eval(
                    self._SCRIPT,
                    1,
                    f"api-gateway:rate:{key}",
                    str(window_seconds),
                    str(limit),
                ),
            )
        except RedisError as exc:
            raise ServiceError(
                code="rate_limiter_unavailable",
                message="Request rate limiter is unavailable",
                status_code=503,
            ) from exc
        return bool(result)
