from typing import cast

from redis.asyncio import Redis

REDIS_SOCKET_TIMEOUT_SECONDS = 5
REDIS_CONNECT_TIMEOUT_SECONDS = 5
REDIS_HEALTH_CHECK_INTERVAL_SECONDS = 30


def create_redis_client(url: str, *, decode_responses: bool = False) -> Redis:
    return cast(
        Redis,
        Redis.from_url(
            url,
            decode_responses=decode_responses,
            socket_timeout=REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=REDIS_CONNECT_TIMEOUT_SECONDS,
            health_check_interval=REDIS_HEALTH_CHECK_INTERVAL_SECONDS,
            retry_on_timeout=True,
        ),
    )
