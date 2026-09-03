from datetime import UTC, datetime
from uuid import UUID

from app.api.schemas import (
    BlockoutCreateRequest,
    ProfileUpsertRequest,
    SkillReplaceRequest,
    WeeklyRulesReplaceRequest,
)
from app.domain.models import (
    AvailabilityBlockout,
    InterviewerProfile,
    InterviewerSkill,
    OutboxEvent,
    VerificationStatus,
    WeeklyAvailabilityRule,
    utc_now,
)
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class InterviewerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: UUID) -> InterviewerProfile:
        profile = await self._session.get(InterviewerProfile, user_id)
        if profile is None:
            raise ServiceError(
                code="interviewer_not_found",
                message="Interviewer profile was not found",
                status_code=404,
            )
        return profile

    async def upsert_profile(
        self, user_id: UUID, request: ProfileUpsertRequest
    ) -> InterviewerProfile:
        values = request.model_dump(mode="json")
        values["user_id"] = user_id
        updates = {key: value for key, value in values.items() if key != "user_id"}
        updates["updated_at"] = utc_now()
        result = await self._session.execute(
            insert(InterviewerProfile)
            .values(**values)
            .on_conflict_do_update(index_elements=[InterviewerProfile.user_id], set_=updates)
            .returning(InterviewerProfile)
        )
        await self._session.commit()
        return result.scalar_one()

    async def submit_verification(self, user_id: UUID) -> InterviewerProfile:
        profile = await self._locked_profile(user_id)
        if profile.verification_status not in {
            VerificationStatus.PENDING,
            VerificationStatus.REJECTED,
        }:
            raise self._invalid_transition(
                profile.verification_status, VerificationStatus.UNDER_REVIEW
            )
        profile.verification_status = VerificationStatus.UNDER_REVIEW
        profile.verification_reason = None
        profile.reviewed_by = None
        profile.reviewed_at = None
        await self._session.commit()
        return profile

    async def list_skills(self, user_id: UUID) -> list[InterviewerSkill]:
        return list(
            (
                await self._session.scalars(
                    select(InterviewerSkill)
                    .where(InterviewerSkill.user_id == user_id)
                    .order_by(
                        InterviewerSkill.domain, InterviewerSkill.topic, InterviewerSkill.skill_name
                    )
                )
            ).all()
        )

    async def replace_skills(
        self, user_id: UUID, request: SkillReplaceRequest
    ) -> list[InterviewerSkill]:
        await self.get_profile(user_id)
        await self._session.execute(
            delete(InterviewerSkill).where(InterviewerSkill.user_id == user_id)
        )
        skills = [
            InterviewerSkill(user_id=user_id, **item.model_dump(mode="json"))
            for item in request.skills
        ]
        self._session.add_all(skills)
        await self._session.commit()
        return await self.list_skills(user_id)

    async def list_weekly_rules(self, user_id: UUID) -> list[WeeklyAvailabilityRule]:
        return list(
            (
                await self._session.scalars(
                    select(WeeklyAvailabilityRule)
                    .where(WeeklyAvailabilityRule.user_id == user_id)
                    .order_by(WeeklyAvailabilityRule.weekday, WeeklyAvailabilityRule.start_time)
                )
            ).all()
        )

    async def replace_weekly_rules(
        self, user_id: UUID, request: WeeklyRulesReplaceRequest
    ) -> list[WeeklyAvailabilityRule]:
        await self.get_profile(user_id)
        await self._session.execute(
            delete(WeeklyAvailabilityRule).where(WeeklyAvailabilityRule.user_id == user_id)
        )
        self._session.add_all(
            [WeeklyAvailabilityRule(user_id=user_id, **item.model_dump()) for item in request.rules]
        )
        self._add_event(
            "interviewer.AvailabilityChanged.v1",
            {"user_id": str(user_id), "change": "weekly_rules_replaced"},
        )
        await self._session.commit()
        return await self.list_weekly_rules(user_id)

    async def list_blockouts(self, user_id: UUID) -> list[AvailabilityBlockout]:
        return list(
            (
                await self._session.scalars(
                    select(AvailabilityBlockout)
                    .where(AvailabilityBlockout.user_id == user_id)
                    .order_by(AvailabilityBlockout.starts_at)
                )
            ).all()
        )

    async def create_blockout(
        self, user_id: UUID, request: BlockoutCreateRequest
    ) -> AvailabilityBlockout:
        await self.get_profile(user_id)
        blockout = AvailabilityBlockout(user_id=user_id, **request.model_dump())
        self._session.add(blockout)
        self._add_event(
            "interviewer.AvailabilityChanged.v1",
            {"user_id": str(user_id), "change": "blockout_created"},
        )
        await self._session.commit()
        await self._session.refresh(blockout)
        return blockout

    async def delete_blockout(self, user_id: UUID, blockout_id: UUID) -> None:
        deleted_id = await self._session.scalar(
            delete(AvailabilityBlockout)
            .where(
                AvailabilityBlockout.id == blockout_id,
                AvailabilityBlockout.user_id == user_id,
            )
            .returning(AvailabilityBlockout.id)
        )
        if deleted_id is None:
            raise ServiceError(
                code="blockout_not_found",
                message="Availability blockout was not found",
                status_code=404,
            )
        self._add_event(
            "interviewer.AvailabilityChanged.v1",
            {"user_id": str(user_id), "change": "blockout_deleted"},
        )
        await self._session.commit()

    async def verification_queue(self) -> list[InterviewerProfile]:
        return list(
            (
                await self._session.scalars(
                    select(InterviewerProfile)
                    .where(
                        InterviewerProfile.verification_status == VerificationStatus.UNDER_REVIEW
                    )
                    .order_by(InterviewerProfile.updated_at)
                )
            ).all()
        )

    async def list_profiles(
        self, verification_status: VerificationStatus | None
    ) -> list[InterviewerProfile]:
        statement = select(InterviewerProfile)
        if verification_status is not None:
            statement = statement.where(
                InterviewerProfile.verification_status == verification_status
            )
        return list(
            (
                await self._session.scalars(
                    statement.order_by(
                        InterviewerProfile.verification_status,
                        InterviewerProfile.updated_at,
                        InterviewerProfile.user_id,
                    )
                )
            ).all()
        )

    async def review(
        self, user_id: UUID, admin_id: UUID, target: VerificationStatus, reason: str | None = None
    ) -> InterviewerProfile:
        profile = await self._locked_profile(user_id)
        allowed = {
            VerificationStatus.VERIFIED: {VerificationStatus.UNDER_REVIEW},
            VerificationStatus.REJECTED: {VerificationStatus.UNDER_REVIEW},
            VerificationStatus.SUSPENDED: {VerificationStatus.VERIFIED},
        }
        if profile.verification_status not in allowed.get(target, set()):
            raise self._invalid_transition(profile.verification_status, target)
        profile.verification_status = target
        profile.verification_reason = reason
        profile.reviewed_by = admin_id
        profile.reviewed_at = datetime.now(UTC)
        if target is VerificationStatus.VERIFIED:
            self._add_event("interviewer.InterviewerVerified.v1", {"user_id": str(user_id)})
        elif target is VerificationStatus.SUSPENDED:
            self._add_event(
                "interviewer.InterviewerSuspended.v1",
                {"user_id": str(user_id), "reason": reason or ""},
            )
        await self._session.commit()
        return profile

    async def reactivate(self, user_id: UUID, admin_id: UUID) -> InterviewerProfile:
        profile = await self._locked_profile(user_id)
        if profile.verification_status is not VerificationStatus.SUSPENDED:
            raise self._invalid_transition(profile.verification_status, VerificationStatus.VERIFIED)
        profile.verification_status = VerificationStatus.VERIFIED
        profile.verification_reason = None
        profile.reviewed_by = admin_id
        profile.reviewed_at = datetime.now(UTC)
        self._add_event(
            "interviewer.InterviewerVerified.v1", {"user_id": str(user_id), "reactivated": True}
        )
        await self._session.commit()
        return profile

    async def _locked_profile(self, user_id: UUID) -> InterviewerProfile:
        profile = await self._session.scalar(
            select(InterviewerProfile)
            .where(InterviewerProfile.user_id == user_id)
            .with_for_update()
        )
        if profile is None:
            raise ServiceError(
                code="interviewer_not_found",
                message="Interviewer profile was not found",
                status_code=404,
            )
        return profile

    def _add_event(self, event_type: str, payload: dict[str, object]) -> None:
        self._session.add(
            OutboxEvent(
                event_type=event_type,
                event_version=1,
                correlation_id=get_correlation_id(),
                payload=payload,
            )
        )

    @staticmethod
    def _invalid_transition(
        current: VerificationStatus, target: VerificationStatus
    ) -> ServiceError:
        return ServiceError(
            code="invalid_verification_transition",
            message=f"Cannot transition verification from {current.value} to {target.value}",
            status_code=409,
        )
