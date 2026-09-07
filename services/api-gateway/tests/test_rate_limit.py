from typing import Any

import pytest
from app.rate_limit import RedisRateLimiter


class ExpiringRedis:
    def __init__(self) -> None:
        self.now = 0
        self.values: dict[str, tuple[int, int]] = {}

    async def eval(self, _script: str, _key_count: int, key: str, ttl: str, limit: str) -> Any:
        current, expires_at = self.values.get(key, (0, self.now + int(ttl)))
        if expires_at <= self.now:
            current, expires_at = 0, self.now + int(ttl)
        current += 1
        self.values[key] = (current, expires_at)
        return 1 if current <= int(limit) else None


@pytest.mark.asyncio
async def test_redis_window_enforces_limit_then_expires() -> None:
    redis = ExpiringRedis()
    limiter = RedisRateLimiter(redis)  # type: ignore[arg-type]

    assert await limiter.allow("user:one", limit=2, window_seconds=5)
    assert await limiter.allow("user:one", limit=2, window_seconds=5)
    assert not await limiter.allow("user:one", limit=2, window_seconds=5)
    assert redis.values["api-gateway:rate:user:one"] == (3, 5)

    redis.now = 5
    assert await limiter.allow("user:one", limit=2, window_seconds=5)
    assert redis.values["api-gateway:rate:user:one"] == (1, 10)
