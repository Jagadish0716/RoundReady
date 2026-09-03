import pytest
from redis.asyncio.connection import SSLConnection
from roundready_common.messaging import connect_rabbit
from roundready_common.redis import create_redis_client


@pytest.mark.asyncio
async def test_rabbit_connection_uses_bounded_reconnect(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    async def fake_connect(url: str, **kwargs: object) -> object:
        calls["url"] = url
        calls.update(kwargs)
        return object()

    monkeypatch.setattr("aio_pika.connect_robust", fake_connect)
    await connect_rabbit("amqps://user:strong-password@rabbit.internal/vhost")

    assert calls == {
        "url": "amqps://user:strong-password@rabbit.internal/vhost",
        "timeout": 10,
        "reconnect_interval": 5,
        "fail_fast": False,
    }


def test_redis_client_uses_bounded_tls_capable_connection_options() -> None:
    client = create_redis_client("rediss://user:strong-password@redis.internal:6380/0")
    options = client.connection_pool.connection_kwargs

    assert options["socket_timeout"] == 5
    assert options["socket_connect_timeout"] == 5
    assert options["health_check_interval"] == 30
    assert options["retry_on_timeout"] is True
    assert client.connection_pool.connection_class is SSLConnection

    import asyncio

    asyncio.run(client.aclose())
