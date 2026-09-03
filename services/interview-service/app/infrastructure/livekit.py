from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
import jwt
from app.domain.providers import ParticipantAccess, VideoRoom


class LiveKitAdapter:
    name = "livekit"

    def __init__(
        self,
        url: str,
        api_key: str,
        api_secret: str,
        token_ttl_seconds: int,
        test_mode: bool,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not url or not api_key or not api_secret:
            raise ValueError("LiveKit URL and credentials are required")
        self._url = url.rstrip("/")
        self._api_url = self._url.replace("wss://", "https://", 1).replace("ws://", "http://", 1)
        self._key = api_key
        self._secret = api_secret
        self._ttl = token_ttl_seconds
        self._test_mode = test_mode
        self._transport = transport

    def _server_token(self) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "iss": self._key,
                "sub": "interview-service",
                "nbf": now,
                "exp": now + timedelta(minutes=2),
                "video": {"roomCreate": True, "roomList": True},
            },
            self._secret,
            algorithm="HS256",
        )

    async def create_room(
        self, *, room_name: str, starts_at: datetime, ends_at: datetime
    ) -> VideoRoom:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0), transport=self._transport
        ) as client:
            response = await client.post(
                f"{self._api_url}/twirp/livekit.RoomService/CreateRoom",
                headers={"Authorization": f"Bearer {self._server_token()}"},
                json={
                    "name": room_name,
                    "emptyTimeout": 300,
                    "departureTimeout": 30,
                    "maxParticipants": 2,
                    "metadata": "recording_disabled",
                    "roomPreset": "",
                    "minPlayoutDelay": 0,
                    "maxPlayoutDelay": 0,
                    "syncStreams": False,
                },
            )
            if response.status_code == 409:
                return VideoRoom(room_name, self._url)
            response.raise_for_status()
            data = self._response_object(response)
            if data.get("name") != room_name:
                raise ValueError("LiveKit returned an invalid room response")
        return VideoRoom(room_name, self._url)

    def create_participant_token(
        self, *, room_reference: str, identity: str, display_name: str
    ) -> ParticipantAccess:
        now = datetime.now(UTC)
        expires = now + timedelta(seconds=self._ttl)
        token = jwt.encode(
            {
                "iss": self._key,
                "sub": identity,
                "name": display_name,
                "jti": str(uuid4()),
                "nbf": now,
                "exp": expires,
                "video": {
                    "roomJoin": True,
                    "room": room_reference,
                    "canPublish": True,
                    "canSubscribe": True,
                    "canPublishData": True,
                    "canUpdateOwnMetadata": False,
                },
                "metadata": "recording_disabled",
            },
            self._secret,
            algorithm="HS256",
        )
        return ParticipantAccess(token, expires, self._url)

    @staticmethod
    def _response_object(response: httpx.Response) -> dict[str, Any]:
        try:
            value = response.json()
        except ValueError as exc:
            raise ValueError("LiveKit returned invalid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("LiveKit returned an invalid response")
        return value


# Backward-compatible name for existing imports.
LiveKitDevelopmentAdapter = LiveKitAdapter
