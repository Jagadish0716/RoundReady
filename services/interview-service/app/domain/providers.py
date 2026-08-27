from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class VideoRoom:
    reference: str
    join_url: str


@dataclass(frozen=True)
class ParticipantAccess:
    token: str
    expires_at: datetime
    join_url: str


class VideoProvider(Protocol):
    name: str

    async def create_room(
        self, *, room_name: str, starts_at: datetime, ends_at: datetime
    ) -> VideoRoom: ...
    def create_participant_token(
        self, *, room_reference: str, identity: str, display_name: str
    ) -> ParticipantAccess: ...
