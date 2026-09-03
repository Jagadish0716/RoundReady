from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.infrastructure.livekit import LiveKitAdapter


def adapter(transport: httpx.AsyncBaseTransport) -> LiveKitAdapter:
    return LiveKitAdapter(
        "wss://roundready.livekit.cloud",
        "configured-livekit-key",
        "configured-livekit-secret-at-least-32-bytes",
        300,
        False,
        transport=transport,
    )


@pytest.mark.asyncio
async def test_create_room_uses_server_derived_name_and_disables_recording() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert (
            request.url == "https://roundready.livekit.cloud/twirp/livekit.RoomService/CreateRoom"
        )
        assert request.headers["Authorization"].startswith("Bearer ")
        data = request.content.decode()
        assert '"name":"interview-booking-id"' in data
        assert "recording_disabled" in data
        return httpx.Response(200, json={"name": "interview-booking-id"})

    room = await adapter(httpx.MockTransport(handler)).create_room(
        room_name="interview-booking-id",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(minutes=20),
    )
    assert room.reference == "interview-booking-id"
    assert room.join_url == "wss://roundready.livekit.cloud"


@pytest.mark.asyncio
async def test_existing_deterministic_room_is_reused() -> None:
    provider = adapter(httpx.MockTransport(lambda _request: httpx.Response(409)))
    room = await provider.create_room(
        room_name="interview-booking-id",
        starts_at=datetime.now(UTC),
        ends_at=datetime.now(UTC) + timedelta(minutes=20),
    )
    assert room.reference == "interview-booking-id"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "response",
    [httpx.Response(200, text="invalid"), httpx.Response(200, json={"name": "wrong-room"})],
)
async def test_invalid_room_response_is_rejected(response: httpx.Response) -> None:
    provider = adapter(httpx.MockTransport(lambda _request: response))
    with pytest.raises(ValueError, match="LiveKit returned"):
        await provider.create_room(
            room_name="interview-booking-id",
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(minutes=20),
        )


@pytest.mark.asyncio
async def test_livekit_network_failure_is_propagated_for_controlled_mapping() -> None:
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("provider unavailable", request=request)

    provider = adapter(httpx.MockTransport(timeout))
    with pytest.raises(httpx.ConnectTimeout):
        await provider.create_room(
            room_name="interview-booking-id",
            starts_at=datetime.now(UTC),
            ends_at=datetime.now(UTC) + timedelta(minutes=20),
        )


def test_adapter_requires_credentials() -> None:
    with pytest.raises(ValueError, match="credentials"):
        LiveKitAdapter("", "", "", 300, False)
