from datetime import UTC, datetime
from uuid import UUID

from app.api.schemas import (
    BlockoutCreateRequest,
    EvidenceInput,
    ProfileUpsertRequest,
    SkillReplaceRequest,
    VerificationReviewRequest,
    WeeklyRulesReplaceRequest,
)
from app.domain.models import (
    AvailabilityBlockout,
    EvidenceStatus,
    InterviewerProfile,
    InterviewerSkill,
    InterviewerVerification,
    OutboxEvent,
    ScreeningCall,
    ScreeningStatus,
    VerificationCheck,
    VerificationCheckType,
    VerificationEvidence,
    VerificationReviewHistory,
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
        verification = await self._verification(user_id)
        verification.status = VerificationStatus.UNDER_REVIEW.value
        verification.submitted_at = datetime.now(UTC)
        verification.rejection_reason = None
        verification.updated_at = datetime.now(UTC)
        self._add_event("interviewer.verification.submitted.v1", {"interviewer_id": str(user_id)})
        await self._session.commit()
        return profile

    async def get_verification(
        self, user_id: UUID, include_history: bool = False
    ) -> dict[str, object]:
        await self.get_profile(user_id)
        verification = await self._verification(user_id)
        evidence = list(
            (
                await self._session.scalars(
                    select(VerificationEvidence)
                    .where(VerificationEvidence.interviewer_id == user_id)
                    .order_by(VerificationEvidence.created_at)
                )
            ).all()
        )
        checks = list(
            (
                await self._session.scalars(
                    select(VerificationCheck)
                    .where(VerificationCheck.interviewer_id == user_id)
                    .order_by(VerificationCheck.check_type)
                )
            ).all()
        )
        screening = await self._session.scalar(
            select(ScreeningCall).where(ScreeningCall.interviewer_id == user_id)
        )
        history: list[VerificationReviewHistory] = []
        if include_history:
            history = list(
                (
                    await self._session.scalars(
                        select(VerificationReviewHistory)
                        .where(VerificationReviewHistory.interviewer_id == user_id)
                        .order_by(VerificationReviewHistory.created_at.desc())
                    )
                ).all()
            )
        return {
            "interviewer_id": user_id,
            "status": verification.status,
            "submitted_at": verification.submitted_at,
            "reviewed_at": verification.reviewed_at,
            "rejection_reason": verification.rejection_reason,
            "suspension_reason": verification.suspension_reason,
            "evidence": evidence,
            "checks": checks,
            "screening": screening,
            "history": history,
        }

    async def upsert_evidence(self, user_id: UUID, request: EvidenceInput) -> dict[str, object]:
        await self.get_profile(user_id)
        verification = await self._verification(user_id)
        if verification.status in {
            VerificationStatus.VERIFIED.value,
            VerificationStatus.SUSPENDED.value,
        }:
            raise ServiceError(
                code="verification_locked",
                message="Verified or suspended evidence cannot be changed",
                status_code=409,
            )
        row = await self._session.scalar(
            select(VerificationEvidence).where(
                VerificationEvidence.interviewer_id == user_id,
                VerificationEvidence.evidence_type == request.evidence_type.value,
            )
        )
        if row is None:
            row = VerificationEvidence(
                interviewer_id=user_id,
                evidence_type=request.evidence_type.value,
                value_reference=request.value_reference,
            )
            self._session.add(row)
        else:
            row.value_reference = request.value_reference
            row.status = EvidenceStatus.PENDING.value
            row.reviewer_notes = None
            row.reviewed_at = None
            row.reviewed_by = None
        verification.updated_at = datetime.now(UTC)
        await self._session.commit()
        return await self.get_verification(user_id)

    async def review_verification(
        self, user_id: UUID, admin_id: UUID, request: VerificationReviewRequest
    ) -> dict[str, object]:
        self._prevent_self_review(user_id, admin_id)
        profile = await self._locked_profile(user_id)
        verification = await self._verification(user_id)
        now = datetime.now(UTC)
        for check_type, passed in request.checks.items():
            statement = (
                insert(VerificationCheck)
                .values(
                    interviewer_id=user_id,
                    check_type=check_type.value,
                    passed=passed,
                    reviewed_by=admin_id,
                    reviewed_at=now,
                )
                .on_conflict_do_update(
                    constraint="uq_verification_check_type",
                    set_={"passed": passed, "reviewed_by": admin_id, "reviewed_at": now},
                )
            )
            await self._session.execute(statement)
        for evidence_id, evidence_status in request.evidence_statuses.items():
            evidence = await self._session.scalar(
                select(VerificationEvidence).where(
                    VerificationEvidence.id == evidence_id,
                    VerificationEvidence.interviewer_id == user_id,
                )
            )
            if evidence is None:
                raise ServiceError(
                    code="evidence_not_found",
                    message="Verification evidence was not found",
                    status_code=404,
                )
            evidence.status = evidence_status.value
            evidence.reviewed_by = admin_id
            evidence.reviewed_at = now
            evidence.reviewer_notes = request.reason
        if request.screening:
            screening = await self._session.scalar(
                select(ScreeningCall).where(ScreeningCall.interviewer_id == user_id)
            )
            if screening is None:
                screening = ScreeningCall(interviewer_id=user_id)
                self._session.add(screening)
            for key, value in request.screening.model_dump(mode="json").items():
                setattr(screening, key, value)
            screening.reviewed_by = admin_id
            screening.reviewed_at = now
            await self._session.flush()
            await self._set_check(
                user_id,
                VerificationCheckType.SCREENING_CALL_PASSED,
                request.screening.screening_status is ScreeningStatus.PASSED,
                admin_id,
                now,
            )
        targets = {
            "under_review": VerificationStatus.UNDER_REVIEW,
            "verify": VerificationStatus.VERIFIED,
            "reject": VerificationStatus.REJECTED,
            "request_more_evidence": VerificationStatus.PENDING,
            "suspend": VerificationStatus.SUSPENDED,
            "reactivate": VerificationStatus.VERIFIED,
        }
        target = targets[request.action]
        allowed_actions = {
            VerificationStatus.PENDING.value: {"under_review"},
            VerificationStatus.UNDER_REVIEW.value: {
                "verify",
                "reject",
                "request_more_evidence",
            },
            VerificationStatus.REJECTED.value: {"under_review"},
            VerificationStatus.VERIFIED.value: {"suspend"},
            VerificationStatus.SUSPENDED.value: {"reactivate"},
        }
        if request.action not in allowed_actions.get(verification.status, set()):
            raise ServiceError(
                code="invalid_verification_transition",
                message=(
                    f"Cannot apply {request.action} while verification is {verification.status}"
                ),
                status_code=409,
            )
        if request.action == "verify":
            passed_checks = set(
                (
                    await self._session.scalars(
                        select(VerificationCheck.check_type).where(
                            VerificationCheck.interviewer_id == user_id,
                            VerificationCheck.passed.is_(True),
                        )
                    )
                ).all()
            )
            required = {
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value,
                VerificationCheckType.SCREENING_CALL_PASSED.value,
            }
            if not required <= passed_checks:
                raise ServiceError(
                    code="verification_checks_incomplete",
                    message="Professional evidence review and screening pass are required",
                    status_code=409,
                )
        if request.action in {"reject", "request_more_evidence", "suspend"} and not request.reason:
            raise ServiceError(
                code="review_reason_required",
                message="A review reason is required",
                status_code=422,
            )
        previous = verification.status
        verification.status = target.value
        verification.reviewed_by = admin_id
        verification.reviewed_at = now
        verification.updated_at = now
        verification.rejection_reason = (
            request.reason
            if target is VerificationStatus.REJECTED or request.action == "request_more_evidence"
            else None
        )
        verification.suspension_reason = (
            request.reason if target is VerificationStatus.SUSPENDED else None
        )
        profile.verification_status = target
        profile.verification_reason = request.reason
        profile.reviewed_by = admin_id
        profile.reviewed_at = now
        self._session.add(
            VerificationReviewHistory(
                interviewer_id=user_id,
                action=request.action,
                from_status=previous,
                to_status=target.value,
                reviewed_by=admin_id,
                notes=request.reason,
            )
        )
        if target is VerificationStatus.VERIFIED:
            self._add_event(
                "interviewer.verification.approved.v1", {"interviewer_id": str(user_id)}
            )
        elif target in {VerificationStatus.REJECTED, VerificationStatus.SUSPENDED}:
            self._add_event(
                f"interviewer.verification.{target.value}.v1", {"interviewer_id": str(user_id)}
            )
        await self._session.commit()
        return await self.get_verification(user_id, include_history=True)

    async def candidate_trust(self, user_id: UUID) -> dict[str, object]:
        verification = await self._verification(user_id)
        if verification.status != VerificationStatus.VERIFIED.value:
            raise ServiceError(
                code="interviewer_not_found", message="Interviewer was not found", status_code=404
            )
        passed = set(
            (
                await self._session.scalars(
                    select(VerificationCheck.check_type).where(
                        VerificationCheck.interviewer_id == user_id,
                        VerificationCheck.passed.is_(True),
                    )
                )
            ).all()
        )
        return {
            "interviewer_id": user_id,
            "roundready_verified": True,
            "contact_verified": bool(
                {
                    VerificationCheckType.EMAIL_VERIFIED.value,
                    VerificationCheckType.MOBILE_VERIFIED.value,
                }
                & passed
            ),
            "professional_experience_reviewed": (
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value in passed
            ),
            "screening_passed": VerificationCheckType.SCREENING_CALL_PASSED.value in passed,
        }

    async def _verification(self, user_id: UUID) -> InterviewerVerification:
        row = await self._session.scalar(
            select(InterviewerVerification)
            .where(InterviewerVerification.interviewer_id == user_id)
            .with_for_update()
        )
        if row is None:
            row = InterviewerVerification(interviewer_id=user_id)
            self._session.add(row)
            await self._session.flush()
        return row

    async def _set_check(
        self,
        user_id: UUID,
        check_type: VerificationCheckType,
        passed: bool,
        admin_id: UUID,
        now: datetime,
    ) -> None:
        await self._session.execute(
            insert(VerificationCheck)
            .values(
                interviewer_id=user_id,
                check_type=check_type.value,
                passed=passed,
                reviewed_by=admin_id,
                reviewed_at=now,
            )
            .on_conflict_do_update(
                constraint="uq_verification_check_type",
                set_={"passed": passed, "reviewed_by": admin_id, "reviewed_at": now},
            )
        )

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
        self._prevent_self_review(user_id, admin_id)
        profile = await self._locked_profile(user_id)
        allowed = {
            VerificationStatus.VERIFIED: {VerificationStatus.UNDER_REVIEW},
            VerificationStatus.REJECTED: {VerificationStatus.UNDER_REVIEW},
            VerificationStatus.SUSPENDED: {VerificationStatus.VERIFIED},
        }
        if profile.verification_status not in allowed.get(target, set()):
            raise self._invalid_transition(profile.verification_status, target)
        if target is VerificationStatus.VERIFIED:
            passed = set(
                (
                    await self._session.scalars(
                        select(VerificationCheck.check_type).where(
                            VerificationCheck.interviewer_id == user_id,
                            VerificationCheck.passed.is_(True),
                        )
                    )
                ).all()
            )
            required = {
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value,
                VerificationCheckType.SCREENING_CALL_PASSED.value,
            }
            if not required <= passed:
                raise ServiceError(
                    code="verification_checks_incomplete",
                    message="Professional evidence review and screening pass are required",
                    status_code=409,
                )
        profile.verification_status = target
        profile.verification_reason = reason
        profile.reviewed_by = admin_id
        profile.reviewed_at = datetime.now(UTC)
        verification = await self._verification(user_id)
        previous = verification.status
        verification.status = target.value
        verification.reviewed_by = admin_id
        verification.reviewed_at = profile.reviewed_at
        verification.updated_at = profile.reviewed_at
        verification.rejection_reason = reason if target is VerificationStatus.REJECTED else None
        verification.suspension_reason = reason if target is VerificationStatus.SUSPENDED else None
        self._session.add(
            VerificationReviewHistory(
                interviewer_id=user_id,
                action=target.value,
                from_status=previous,
                to_status=target.value,
                reviewed_by=admin_id,
                notes=reason,
            )
        )
        if target is VerificationStatus.VERIFIED:
            self._add_event("interviewer.InterviewerVerified.v1", {"user_id": str(user_id)})
            self._add_event(
                "interviewer.verification.approved.v1", {"interviewer_id": str(user_id)}
            )
        elif target is VerificationStatus.REJECTED:
            self._add_event(
                "interviewer.verification.rejected.v1", {"interviewer_id": str(user_id)}
            )
        elif target is VerificationStatus.SUSPENDED:
            self._add_event(
                "interviewer.InterviewerSuspended.v1",
                {"user_id": str(user_id), "reason": reason or ""},
            )
            self._add_event(
                "interviewer.verification.suspended.v1", {"interviewer_id": str(user_id)}
            )
        await self._session.commit()
        return profile

    async def reactivate(self, user_id: UUID, admin_id: UUID) -> InterviewerProfile:
        self._prevent_self_review(user_id, admin_id)
        profile = await self._locked_profile(user_id)
        if profile.verification_status is not VerificationStatus.SUSPENDED:
            raise self._invalid_transition(profile.verification_status, VerificationStatus.VERIFIED)
        profile.verification_status = VerificationStatus.VERIFIED
        profile.verification_reason = None
        profile.reviewed_by = admin_id
        profile.reviewed_at = datetime.now(UTC)
        verification = await self._verification(user_id)
        previous = verification.status
        verification.status = VerificationStatus.VERIFIED.value
        verification.suspension_reason = None
        verification.reviewed_by = admin_id
        verification.reviewed_at = profile.reviewed_at
        verification.updated_at = profile.reviewed_at
        self._session.add(
            VerificationReviewHistory(
                interviewer_id=user_id,
                action="reactivate",
                from_status=previous,
                to_status=VerificationStatus.VERIFIED.value,
                reviewed_by=admin_id,
            )
        )
        self._add_event(
            "interviewer.InterviewerVerified.v1", {"user_id": str(user_id), "reactivated": True}
        )
        self._add_event("interviewer.verification.approved.v1", {"interviewer_id": str(user_id)})
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
    def _prevent_self_review(user_id: UUID, admin_id: UUID) -> None:
        if user_id == admin_id:
            raise ServiceError(
                code="verification_self_review_forbidden",
                message="Interviewers cannot review their own verification",
                status_code=403,
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
