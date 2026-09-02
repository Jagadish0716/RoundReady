from datetime import UTC, datetime, timedelta

import jwt
from app.domain.providers import ParticipantAccess, VideoRoom


class DevelopmentVideoProvider:
    """Local room/token provider with no LiveKit network dependency."""

    name = "development"

    def __init__(self, url: str, key: str, secret: str, ttl_seconds: int) -> None:
        if not secret:
            raise ValueError("Development video secret is required")
        self._url, self._key, self._secret, self._ttl = url, key, secret, ttl_seconds

    async def create_room(
        self, *, room_name: str, starts_at: datetime, ends_at: datetime
    ) -> VideoRoom:
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
                "nbf": now,
                "exp": expires,
                "video": {"roomJoin": True, "room": room_reference},
                "metadata": "recording_disabled",
            },
            self._secret,
            algorithm="HS256",
        )
        return ParticipantAccess(token, expires, self._url)
