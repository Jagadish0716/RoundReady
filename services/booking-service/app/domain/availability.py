from datetime import datetime
from typing import Protocol
from uuid import UUID


class AvailabilityWindow(Protocol):
    starts_at: datetime
    ends_at: datetime


class InterviewerAvailabilityProvider(Protocol):
    """Boundary for the interviewer-service availability API; never a database adapter."""

    async def windows(
        self, interviewer_id: UUID, starts_at: datetime, ends_at: datetime
    ) -> list[AvailabilityWindow]: ...
