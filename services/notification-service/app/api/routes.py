from datetime import datetime
from uuid import UUID

from app.application.notification_reader import NotificationReader
from app.dependencies import AuthenticatedIdentity, DatabaseSession
from app.domain.models import Notification
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    channel: str
    rendered_subject: str | None
    rendered_body: str
    status: str
    created_at: datetime
    read_at: datetime | None


@router.get("/me", response_model=list[NotificationResponse])
async def list_my_notifications(
    identity: AuthenticatedIdentity, session: DatabaseSession
) -> list[Notification]:
    return await NotificationReader(session).list_owned(identity.user_id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_my_notification_read(
    notification_id: UUID,
    identity: AuthenticatedIdentity,
    session: DatabaseSession,
) -> Notification:
    return await NotificationReader(session).mark_read(notification_id, identity.user_id)
