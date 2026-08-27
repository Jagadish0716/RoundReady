from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class AuthenticatedRole(StrEnum):
    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    ADMIN = "admin"


@dataclass(frozen=True)
class InternalIdentity:
    user_id: UUID
    role: AuthenticatedRole
