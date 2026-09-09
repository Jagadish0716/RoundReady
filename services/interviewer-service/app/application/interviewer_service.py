import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import phonenumbers
from app.api.schemas import (
    BlockoutCreateRequest,
    ChallengeResponse,
    EvidenceInput,
    ProfileUpsertRequest,
    ScreeningReviewRequest,
    SkillReplaceRequest,
    VerificationReviewRequest,
    WeeklyRulesReplaceRequest,
)
from app.config import Settings
from app.domain.models import (
    AvailabilityBlockout,
    ContactVerificationChallenge,
    EvidenceStatus,
    InterviewerContactVerification,
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
from app.infrastructure.contact_verification import DevelopmentContactVerificationProvider
from pydantic import ValidationError
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class InterviewerService:
    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings

    async def contact_verification(
        self,
        user_id: UUID,
        account_email: str | None = None,
        account_email_verified: bool | None = None,
    ) -> dict[str, object]:
        await self.get_profile(user_id)
        if account_email_verified is not None:
            await self._set_ownership_check(
                user_id, VerificationCheckType.EMAIL_VERIFIED, account_email_verified
            )
            await self._session.commit()
        contact = await self._session.get(InterviewerContactVerification, user_id)
        check = await self._session.scalar(
            select(VerificationCheck).where(
                VerificationCheck.interviewer_id == user_id,
                VerificationCheck.check_type == VerificationCheckType.EMAIL_VERIFIED,
            )
        )
        return {
            "account_email": account_email,
            "account_email_verified": bool(check and check.passed),
            "mobile_e164": contact.mobile_e164 if contact else None,
            "mobile_verified": bool(contact and contact.mobile_verified_at),
            "company_email": contact.company_email if contact else None,
            "company_email_verified": bool(contact and contact.company_email_verified_at),
        }

    async def request_mobile_verification(self, user_id: UUID, mobile: str) -> ChallengeResponse:
        try:
            parsed = phonenumbers.parse(mobile, None)
        except phonenumbers.NumberParseException as exc:
            raise ServiceError(
                code="invalid_mobile", message="Enter a valid mobile number", status_code=422
            ) from exc
        if not phonenumbers.is_valid_number(parsed):
            raise ServiceError(
                code="invalid_mobile", message="Enter a valid mobile number", status_code=422
            )
        canonical = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        if canonical.startswith("+91") and not re.fullmatch(r"\+91[6-9]\d{9}", canonical):
            raise ServiceError(
                code="invalid_mobile", message="Enter a valid Indian mobile number", status_code=422
            )
        contact = await self._contact(user_id)
        if contact.mobile_e164 != canonical:
            contact.mobile_e164 = canonical
            contact.mobile_verified_at = None
            await self._set_ownership_check(user_id, VerificationCheckType.MOBILE_VERIFIED, False)
        return await self._create_challenge(user_id, "mobile", canonical)

    async def request_company_email_verification(
        self, user_id: UUID, company_email: str
    ) -> ChallengeResponse:
        contact = await self._contact(user_id)
        normalized = company_email.strip().casefold()
        if contact.company_email != normalized:
            contact.company_email = normalized
            contact.company_email_verified_at = None
            await self._set_ownership_check(
                user_id, VerificationCheckType.COMPANY_EMAIL_VERIFIED, False
            )
        return await self._create_challenge(user_id, "company_email", normalized)

    async def verify_contact_challenge(
        self, user_id: UUID, challenge_id: UUID, secret_value: str
    ) -> dict[str, object]:
        now = datetime.now(UTC)
        challenge = await self._session.scalar(
            select(ContactVerificationChallenge)
            .where(
                ContactVerificationChallenge.id == challenge_id,
                ContactVerificationChallenge.interviewer_id == user_id,
            )
            .with_for_update()
        )
        if challenge is None or challenge.consumed_at is not None:
            raise ServiceError(
                code="invalid_verification_challenge",
                message="Verification code or link is invalid",
                status_code=422,
            )
        settings = self._contact_settings()
        if challenge.expires_at <= now:
            raise ServiceError(
                code="verification_challenge_expired",
                message="Verification code or link has expired",
                status_code=422,
            )
        if challenge.attempt_count >= settings.contact_max_attempts:
            raise ServiceError(
                code="verification_attempts_exhausted",
                message="Too many verification attempts",
                status_code=429,
            )
        challenge.attempt_count += 1
        supplied = self._secret_hash(user_id, challenge.kind, secret_value)
        if not hmac.compare_digest(supplied, challenge.secret_hash):
            await self._session.commit()
            raise ServiceError(
                code="invalid_verification_challenge",
                message="Verification code or link is invalid",
                status_code=422,
            )
        contact = await self._contact(user_id)
        fingerprint = self._fingerprint(
            contact.mobile_e164 if challenge.kind == "mobile" else contact.company_email
        )
        if not hmac.compare_digest(fingerprint, challenge.target_fingerprint):
            raise ServiceError(
                code="verification_target_changed",
                message="Contact value changed; request a new verification",
                status_code=409,
            )
        challenge.consumed_at = now
        if challenge.kind == "mobile":
            contact.mobile_verified_at = now
            await self._set_ownership_check(user_id, VerificationCheckType.MOBILE_VERIFIED, True)
        else:
            contact.company_email_verified_at = now
            await self._set_ownership_check(
                user_id, VerificationCheckType.COMPANY_EMAIL_VERIFIED, True
            )
        await self._session.commit()
        return await self.contact_verification(user_id)

    async def _contact(self, user_id: UUID) -> InterviewerContactVerification:
        await self.get_profile(user_id)
        contact = await self._session.get(InterviewerContactVerification, user_id)
        if contact is None:
            contact = InterviewerContactVerification(interviewer_id=user_id)
            self._session.add(contact)
            await self._session.flush()
        return contact

    async def _create_challenge(self, user_id: UUID, kind: str, target: str) -> ChallengeResponse:
        settings = self._contact_settings()
        if settings.environment != "development":
            raise ServiceError(
                code="contact_verification_provider_unavailable",
                message="Contact verification delivery is not configured",
                status_code=503,
            )
        now = datetime.now(UTC)
        latest = await self._session.scalar(
            select(ContactVerificationChallenge)
            .where(
                ContactVerificationChallenge.interviewer_id == user_id,
                ContactVerificationChallenge.kind == kind,
                ContactVerificationChallenge.consumed_at.is_(None),
            )
            .order_by(ContactVerificationChallenge.created_at.desc())
            .limit(1)
        )
        if latest and latest.resend_available_at > now:
            raise ServiceError(
                code="verification_resend_cooldown",
                message="Wait before requesting another verification",
                status_code=429,
            )
        if latest:
            latest.consumed_at = now
        secret_value = (
            f"{secrets.randbelow(1_000_000):06d}" if kind == "mobile" else secrets.token_urlsafe(32)
        )
        challenge = ContactVerificationChallenge(
            interviewer_id=user_id,
            kind=kind,
            target_fingerprint=self._fingerprint(target),
            secret_hash=self._secret_hash(user_id, kind, secret_value),
            expires_at=now + timedelta(seconds=settings.contact_challenge_ttl_seconds),
            resend_available_at=now + timedelta(seconds=settings.contact_resend_cooldown_seconds),
        )
        self._session.add(challenge)
        await self._session.commit()
        await self._session.refresh(challenge)
        provider = DevelopmentContactVerificationProvider()
        development_secret = (
            await provider.deliver_mobile_code(target, secret_value)
            if kind == "mobile"
            else await provider.deliver_company_email_token(target, secret_value)
        )
        return ChallengeResponse(
            challenge_id=challenge.id,
            expires_at=challenge.expires_at,
            resend_available_at=challenge.resend_available_at,
            development_secret=development_secret,
        )

    async def _set_ownership_check(
        self, user_id: UUID, check_type: VerificationCheckType, passed: bool
    ) -> None:
        await self._session.execute(
            insert(VerificationCheck)
            .values(
                interviewer_id=user_id,
                check_type=check_type.value,
                passed=passed,
                reviewed_by=None,
                reviewed_at=datetime.now(UTC),
            )
            .on_conflict_do_update(
                constraint="uq_verification_check_type",
                set_={"passed": passed, "reviewed_by": None, "reviewed_at": datetime.now(UTC)},
            )
        )
        self._add_event(
            "interviewer.contact_verification.changed.v1",
            {
                "interviewer_id": str(user_id),
                "check_type": check_type.value,
                "state": "verified" if passed else "pending",
            },
        )

    def _contact_settings(self) -> Settings:
        if self._settings is None:
            raise RuntimeError("contact verification settings are required")
        return self._settings

    def _secret_hash(self, user_id: UUID, kind: str, value: str) -> str:
        key = self._contact_settings().contact_verification_secret.get_secret_value().encode()
        return hmac.new(key, f"{user_id}:{kind}:{value}".encode(), hashlib.sha256).hexdigest()

    def _fingerprint(self, value: str | None) -> str:
        key = self._contact_settings().contact_verification_secret.get_secret_value().encode()
        return hmac.new(key, (value or "").encode(), hashlib.sha256).hexdigest()

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
        existing = await self._session.get(InterviewerProfile, user_id)
        if existing is not None:
            self._ensure_active(existing)
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
        try:
            ProfileUpsertRequest.model_validate(
                {field: getattr(profile, field) for field in ProfileUpsertRequest.model_fields}
            )
        except ValidationError as exc:
            fields = sorted({str(error["loc"][0]) for error in exc.errors()})
            raise ServiceError(
                code="profile_incomplete",
                message="Complete all required professional profile fields before verification",
                status_code=409,
                details={"fields": fields},
            ) from exc
        passed_contact_checks = set(
            (
                await self._session.scalars(
                    select(VerificationCheck.check_type).where(
                        VerificationCheck.interviewer_id == user_id,
                        VerificationCheck.passed.is_(True),
                    )
                )
            ).all()
        )
        required_contact_checks = {
            VerificationCheckType.EMAIL_VERIFIED.value,
            VerificationCheckType.MOBILE_VERIFIED.value,
            VerificationCheckType.COMPANY_EMAIL_VERIFIED.value,
        }
        if not required_contact_checks <= passed_contact_checks:
            raise ServiceError(
                code="contact_verification_incomplete",
                message="Complete all required contact verification before submission",
                status_code=409,
                details={"checks": sorted(required_contact_checks - passed_contact_checks)},
            )
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
        self._ensure_active(await self.get_profile(user_id))
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
        passed = {item.check_type for item in checks if item.passed}
        required = {item.value for item in VerificationCheckType}
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
            "missing_requirements": sorted(required - passed),
        }

    async def review_linkedin(self, user_id: UUID, admin_id: UUID) -> dict[str, object]:
        self._prevent_self_review(user_id, admin_id)
        profile = await self._locked_profile(user_id)
        if not profile.linkedin_url:
            raise ServiceError(
                code="linkedin_profile_missing",
                message="A LinkedIn profile must exist before it can be reviewed",
                status_code=409,
            )
        await self._set_check(
            user_id, VerificationCheckType.LINKEDIN_REVIEWED, True,
            admin_id, datetime.now(UTC),
        )
        await self._session.commit()
        return await self.get_verification(user_id, include_history=True)

    async def review_evidence(
        self, user_id: UUID, evidence_id: UUID, admin_id: UUID,
        status: EvidenceStatus, notes: str | None,
    ) -> dict[str, object]:
        self._prevent_self_review(user_id, admin_id)
        await self._locked_profile(user_id)
        evidence = await self._session.scalar(
            select(VerificationEvidence).where(
                VerificationEvidence.id == evidence_id,
                VerificationEvidence.interviewer_id == user_id,
            ).with_for_update()
        )
        if evidence is None:
            raise ServiceError(
                code="evidence_not_found",
                message="Verification evidence was not found",
                status_code=404,
            )
        now = datetime.now(UTC)
        evidence.status = status.value
        evidence.reviewer_notes = notes
        evidence.reviewed_at = now
        evidence.reviewed_by = admin_id
        verified_count = await self._session.scalar(
            select(VerificationEvidence.id).where(
                VerificationEvidence.interviewer_id == user_id,
                VerificationEvidence.status == EvidenceStatus.VERIFIED.value,
            ).limit(1)
        )
        await self._set_check(
            user_id, VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED,
            status is EvidenceStatus.VERIFIED or verified_count is not None,
            admin_id, now,
        )
        await self._session.commit()
        return await self.get_verification(user_id, include_history=True)

    async def record_screening(
        self, user_id: UUID, admin_id: UUID, request: ScreeningReviewRequest
    ) -> dict[str, object]:
        self._prevent_self_review(user_id, admin_id)
        await self._locked_profile(user_id)
        screening = await self._session.scalar(
            select(ScreeningCall).where(ScreeningCall.interviewer_id == user_id).with_for_update()
        )
        if screening is None:
            if request.screening_status is not ScreeningStatus.PENDING:
                raise ServiceError(
                    code="screening_not_scheduled",
                    message="Schedule screening before recording its result",
                    status_code=409,
                )
            screening = ScreeningCall(interviewer_id=user_id)
            self._session.add(screening)
        elif (
            request.screening_status in {ScreeningStatus.PASSED, ScreeningStatus.FAILED}
            and screening.screening_status != ScreeningStatus.PENDING.value
        ):
            raise ServiceError(
                code="screening_not_scheduled",
                message="Only a scheduled screening can receive a result",
                status_code=409,
            )
        now = datetime.now(UTC)
        for key, value in request.model_dump(mode="json").items():
            setattr(screening, key, value)
        screening.reviewed_by = admin_id
        screening.reviewed_at = now
        await self._session.flush()
        await self._set_check(
            user_id, VerificationCheckType.SCREENING_CALL_PASSED,
            request.screening_status is ScreeningStatus.PASSED, admin_id, now,
        )
        await self._session.commit()
        return await self.get_verification(user_id, include_history=True)

    async def upsert_evidence(self, user_id: UUID, request: EvidenceInput) -> dict[str, object]:
        self._ensure_active(await self.get_profile(user_id))
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
        if request.checks or request.evidence_statuses or request.screening:
            raise ServiceError(
                code="verification_action_payload_not_allowed",
                message="Use the dedicated review actions before final approval",
                status_code=422,
            )
        for check_type, passed in request.checks.items():
            if check_type in {
                VerificationCheckType.EMAIL_VERIFIED,
                VerificationCheckType.MOBILE_VERIFIED,
                VerificationCheckType.COMPANY_EMAIL_VERIFIED,
            }:
                raise ServiceError(
                    code="ownership_check_not_admin_editable",
                    message="Contact ownership checks require their verification flow",
                    status_code=403,
                )
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
                VerificationCheckType.EMAIL_VERIFIED.value,
                VerificationCheckType.MOBILE_VERIFIED.value,
                VerificationCheckType.LINKEDIN_REVIEWED.value,
                VerificationCheckType.COMPANY_EMAIL_VERIFIED.value,
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value,
                VerificationCheckType.SCREENING_CALL_PASSED.value,
            }
            if not required <= passed_checks:
                missing = sorted(required - passed_checks)
                raise ServiceError(
                    code="verification_prerequisites_incomplete",
                    message="Complete all verification prerequisites before approval",
                    status_code=409,
                    details={"missing": missing},
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
            "contact_verified": {
                VerificationCheckType.EMAIL_VERIFIED.value,
                VerificationCheckType.MOBILE_VERIFIED.value,
                VerificationCheckType.COMPANY_EMAIL_VERIFIED.value,
            }
            <= passed,
            "professional_experience_reviewed": (
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value in passed
            ),
            "screening_passed": VerificationCheckType.SCREENING_CALL_PASSED.value in passed,
        }

    async def public_interviewers(self) -> list[dict[str, object]]:
        profiles = list(
            (
                await self._session.scalars(
                    select(InterviewerProfile)
                    .where(
                        InterviewerProfile.verification_status == VerificationStatus.VERIFIED,
                        InterviewerProfile.deleted_at.is_(None),
                    )
                    .order_by(InterviewerProfile.updated_at.desc())
                )
            ).all()
        )
        return [await self.public_interviewer(profile.user_id) for profile in profiles]

    async def public_interviewer(self, user_id: UUID) -> dict[str, object]:
        profile = await self.get_profile(user_id)
        if (
            profile.verification_status is not VerificationStatus.VERIFIED
            or profile.deleted_at is not None
        ):
            raise ServiceError(
                code="interviewer_not_found",
                message="Interviewer was not found",
                status_code=404,
            )
        trust = await self.candidate_trust(user_id)
        return {
            "interviewer_id": user_id,
            "full_name": profile.full_name,
            "headline": profile.headline,
            "job_title": profile.job_title,
            "experience_years": profile.experience_years,
            "bio": profile.bio,
            "skills": await self.list_skills(user_id),
            "interview_languages": ["English"],
            **trust,
            "price_paise": 20000,
            "currency": "INR",
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
        self._ensure_active(await self.get_profile(user_id))
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
        statement = select(InterviewerProfile).where(InterviewerProfile.deleted_at.is_(None))
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

    async def delete_interviewer(
        self, user_id: UUID, admin_id: UUID, reason: str
    ) -> InterviewerProfile:
        self._prevent_self_review(user_id, admin_id)
        profile = await self._locked_profile(user_id, allow_deleted=True)
        if profile.deleted_at is not None:
            return profile
        if self._settings is None:
            raise RuntimeError("Settings are required for interviewer deletion")
        headers = {
            "X-User-ID": str(admin_id),
            "X-User-Role": "admin",
            "X-Internal-Identity-Secret": (
                self._settings.internal_identity_secret.get_secret_value()
            ),
        }
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    f"{self._settings.booking_service_url.rstrip('/')}/v1/internal/interviewers/"
                    f"{user_id}/active-bookings",
                    headers=headers,
                )
            response.raise_for_status()
            active_count = int(response.json()["active_booking_count"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ServiceError(
                code="booking_safety_check_unavailable",
                message="Could not verify whether the interviewer has active bookings",
                status_code=503,
            ) from exc
        if active_count:
            raise ServiceError(
                code="interviewer_has_active_bookings",
                message="Interviewer has active or future bookings",
                status_code=409,
                details={"active_booking_count": active_count},
            )
        profile.deleted_at = datetime.now(UTC)
        profile.deleted_by_admin_id = admin_id
        profile.deletion_reason = reason
        self._session.add(
            VerificationReviewHistory(
                interviewer_id=user_id,
                action="deleted",
                from_status=profile.verification_status.value,
                to_status=profile.verification_status.value,
                reviewed_by=admin_id,
                notes=reason,
            )
        )
        self._add_event("interviewer.deleted.v1", {"interviewer_id": str(user_id)})
        await self._session.commit()
        return profile

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
                VerificationCheckType.EMAIL_VERIFIED.value,
                VerificationCheckType.MOBILE_VERIFIED.value,
                VerificationCheckType.LINKEDIN_REVIEWED.value,
                VerificationCheckType.COMPANY_EMAIL_VERIFIED.value,
                VerificationCheckType.PROFESSIONAL_EVIDENCE_REVIEWED.value,
                VerificationCheckType.SCREENING_CALL_PASSED.value,
            }
            if not required <= passed:
                missing = sorted(required - passed)
                raise ServiceError(
                    code="verification_prerequisites_incomplete",
                    message="Complete all verification prerequisites before approval",
                    status_code=409,
                    details={"missing": missing},
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

    async def _locked_profile(
        self, user_id: UUID, *, allow_deleted: bool = False
    ) -> InterviewerProfile:
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
        if not allow_deleted:
            self._ensure_active(profile)
        return profile

    @staticmethod
    def _ensure_active(profile: InterviewerProfile) -> None:
        if profile.deleted_at is not None:
            raise ServiceError(
                code="interviewer_deleted",
                message="Deleted interviewer accounts cannot perform this action",
                status_code=409,
            )

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
