import secrets
from collections.abc import Awaitable
from typing import Any, cast

from redis.asyncio import Redis
from redis.exceptions import RedisError
from roundready_common.errors import ServiceError


class RedisHoldStore:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl_seconds = ttl_seconds

    async def acquire(self, slot_id: str, token: str) -> bool:
        try:
            result = await self._redis.set(self.key(slot_id), token, nx=True, ex=self._ttl_seconds)
        except RedisError as exc:
            raise self._unavailable() from exc
        return bool(result)

    async def matches(self, slot_id: str, token: str) -> bool:
        try:
            value = await self._redis.get(self.key(slot_id))
        except RedisError as exc:
            raise self._unavailable() from exc
        actual = value.decode() if isinstance(value, bytes) else value
        return isinstance(actual, str) and secrets.compare_digest(actual, token)

    async def release(self, slot_id: str, token: str) -> bool:
        script = (
            "if redis.call('get', KEYS[1]) == ARGV[1] "
            "then return redis.call('del', KEYS[1]) else return 0 end"
        )
        try:
            result = await cast(
                Awaitable[Any], self._redis.eval(script, 1, self.key(slot_id), token)
            )
        except RedisError as exc:
            raise self._unavailable() from exc
        return bool(result)

    @staticmethod
    def _unavailable() -> ServiceError:
        return ServiceError(
            code="hold_store_unavailable",
            message="Slot hold service is unavailable",
            status_code=503,
        )

    @staticmethod
    def key(slot_id: str) -> str:
        return f"booking-service:slot-hold:{slot_id}"
