from datetime import UTC, datetime
from uuid import UUID

from roundready_common.errors import ServiceError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Notification


class NotificationReader:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_owned(self, user_id: UUID) -> list[Notification]:
        return list(
            (
                await self.session.scalars(
                    select(Notification)
                    .where(Notification.recipient_user_id == user_id)
                    .order_by(Notification.created_at.desc(), Notification.id.desc())
                )
            ).all()
        )

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        record = await self.session.scalar(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.recipient_user_id == user_id,
            )
        )
        if record is None:
            raise ServiceError(
                code="notification_not_found",
                message="Notification was not found",
                status_code=404,
            )
        if record.read_at is None:
            record.read_at = datetime.now(UTC)
            await self.session.commit()
        return record
