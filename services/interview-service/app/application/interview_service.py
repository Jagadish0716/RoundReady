from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from roundready_common.contracts import (
    CANDIDATE_NO_SHOW,
    FEEDBACK_SUBMITTED,
    INTERVIEW_COMPLETED,
    INTERVIEW_STARTED,
    INTERVIEWER_NO_SHOW,
    TECHNICAL_FAILURE,
)
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import FeedbackCreate, RubricCreate, SessionCreate
from app.config import Settings
from app.dependencies import Identity, Role
from app.domain.models import (
    AttendanceEvent,
    FeedbackReport,
    InterviewSession,
    OutboxEvent,
    ParticipantAttendance,
    ParticipantRole,
    ProcessedEvent,
    Rubric,
    SessionStatus,
)
from app.domain.providers import ParticipantAccess, VideoProvider


class InterviewService:
    def __init__(self, session: AsyncSession, provider: VideoProvider, settings: Settings) -> None:
        self.db = session
        self.provider = provider
        self.settings = settings

    async def create_rubric(self, data: RubricCreate) -> Rubric:
        rubric = Rubric(
            domain=data.domain,
            topic=data.topic,
            experience_level=data.experience_level,
            version=data.version,
            criteria=[x.model_dump() for x in data.criteria],
            maximum_score=sum(x.maximum_score for x in data.criteria),
        )
        self.db.add(rubric)
        await self.db.commit()
        return rubric

    async def create_session(self, data: SessionCreate) -> InterviewSession:
        existing: InterviewSession | None
        if await self.db.get(ProcessedEvent, data.event_id):
            existing = await self.db.scalar(
                select(InterviewSession).where(InterviewSession.booking_id == data.booking_id)
            )
            if existing:
                return existing
        if await self.db.get(Rubric, data.rubric_id) is None:
            raise ServiceError(
                code="rubric_not_found", message="Rubric was not found", status_code=404
            )
        existing = await self.db.scalar(
            select(InterviewSession).where(InterviewSession.booking_id == data.booking_id)
        )
        if existing:
            self.db.add(ProcessedEvent(event_id=data.event_id, event_type="BookingConfirmed"))
            await self.db.commit()
            return existing
        room = await self.provider.create_room(
            room_name=f"interview-{data.booking_id}",
            starts_at=data.scheduled_start,
            ends_at=data.scheduled_end,
        )
        item = InterviewSession(
            booking_id=data.booking_id,
            candidate_id=data.candidate_id,
            interviewer_id=data.interviewer_id,
            rubric_id=data.rubric_id,
            room_reference=room.reference,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            status=SessionStatus.READY,
        )
        self.db.add_all(
            [item, ProcessedEvent(event_id=data.event_id, event_type="BookingConfirmed")]
        )
        await self.db.flush()
        self.db.add_all(
            [
                ParticipantAttendance(
                    session_id=item.id, user_id=data.candidate_id, role=ParticipantRole.CANDIDATE
                ),
                ParticipantAttendance(
                    session_id=item.id,
                    user_id=data.interviewer_id,
                    role=ParticipantRole.INTERVIEWER,
                ),
            ]
        )
        await self.db.commit()
        return item

    async def get_session(self, session_id: UUID, identity: Identity) -> InterviewSession:
        item = await self.db.get(InterviewSession, session_id)
        if item is None or (
            identity.role is not Role.ADMIN
            and identity.user_id not in {item.candidate_id, item.interviewer_id}
        ):
            raise ServiceError(
                code="session_not_found", message="Interview session was not found", status_code=404
            )
        return item

    async def list_sessions(self, identity: Identity) -> list[InterviewSession]:
        if identity.role is Role.CANDIDATE:
            condition = InterviewSession.candidate_id == identity.user_id
        elif identity.role is Role.INTERVIEWER:
            condition = InterviewSession.interviewer_id == identity.user_id
        else:
            raise ServiceError(
                code="participant_role_required",
                message="Candidate or interviewer role is required",
                status_code=403,
            )
        return list(
            (
                await self.db.scalars(
                    select(InterviewSession)
                    .where(condition)
                    .order_by(InterviewSession.scheduled_start)
                )
            ).all()
        )

    async def get_rubric_for_session(self, session_id: UUID, identity: Identity) -> Rubric:
        item = await self.get_session(session_id, identity)
        rubric = await self.db.get(Rubric, item.rubric_id)
        if rubric is None:
            raise ServiceError(
                code="rubric_not_found", message="Rubric was not found", status_code=404
            )
        return rubric

    async def transition_by_interviewer(
        self, session_id: UUID, interviewer_id: UUID, target: SessionStatus
    ) -> InterviewSession:
        item = await self.db.get(InterviewSession, session_id)
        if item is None or item.interviewer_id != interviewer_id:
            raise ServiceError(
                code="session_not_found", message="Interview session was not found", status_code=404
            )
        if target not in {SessionStatus.IN_PROGRESS, SessionStatus.COMPLETED}:
            raise ServiceError(
                code="invalid_session_transition",
                message="Interviewer session transition is invalid",
                status_code=409,
            )
        return await self.transition(session_id, target)

    async def join(self, session_id: UUID, identity: Identity) -> ParticipantAccess:
        item = await self.get_session(session_id, identity)
        if identity.role not in {Role.CANDIDATE, Role.INTERVIEWER}:
            raise ServiceError(
                code="participant_role_required",
                message="Candidate or interviewer role is required",
                status_code=403,
            )
        expected = item.candidate_id if identity.role is Role.CANDIDATE else item.interviewer_id
        if identity.user_id != expected:
            raise ServiceError(
                code="session_access_denied",
                message="User is not assigned to this session",
                status_code=403,
            )
        now = datetime.now(UTC)
        if now < item.scheduled_start - timedelta(
            seconds=self.settings.join_window_before_seconds
        ) or now > item.scheduled_end + timedelta(seconds=self.settings.join_window_after_seconds):
            raise ServiceError(
                code="join_window_closed",
                message="Participant token is unavailable outside the join window",
                status_code=409,
            )
        if item.status not in {SessionStatus.READY, SessionStatus.IN_PROGRESS}:
            raise ServiceError(
                code="session_not_joinable",
                message="Interview session is not joinable",
                status_code=409,
            )
        if not item.room_reference:
            raise ServiceError(
                code="room_unavailable", message="Interview room is unavailable", status_code=503
            )
        return self.provider.create_participant_token(
            room_reference=item.room_reference,
            identity=str(identity.user_id),
            display_name=identity.role.value,
        )

    async def attendance(
        self, session_id: UUID, event_id: str, user_id: UUID, event_type: str, occurred_at: datetime
    ) -> ParticipantAttendance:
        duplicate = await self.db.scalar(
            select(AttendanceEvent).where(AttendanceEvent.provider_event_id == event_id)
        )
        if duplicate:
            result = await self.db.get(ParticipantAttendance, duplicate.participant_id)
            assert result
            return result
        item = await self.db.get(InterviewSession, session_id)
        if item is None:
            raise ServiceError(
                code="session_not_found", message="Interview session was not found", status_code=404
            )
        participant = await self.db.scalar(
            select(ParticipantAttendance)
            .where(
                ParticipantAttendance.session_id == session_id,
                ParticipantAttendance.user_id == user_id,
            )
            .with_for_update()
        )
        if participant is None:
            raise ServiceError(
                code="participant_not_assigned",
                message="Participant is not assigned to this session",
                status_code=403,
            )
        when = occurred_at.astimezone(UTC)
        if event_type == "joined":
            if participant.connected:
                return participant
            if participant.first_joined_at is None:
                participant.first_joined_at = when
            else:
                participant.reconnect_count += 1
            participant.last_joined_at = when
            participant.connected = True
            if item.status is SessionStatus.READY:
                item.status = SessionStatus.IN_PROGRESS
                item.actual_start = when
                self._event(INTERVIEW_STARTED, item)
        else:
            if participant.connected and participant.last_joined_at:
                participant.total_connected_seconds += max(
                    0, int((when - participant.last_joined_at).total_seconds())
                )
            participant.last_left_at = when
            participant.connected = False
        self.db.add(
            AttendanceEvent(
                provider_event_id=event_id,
                session_id=item.id,
                participant_id=participant.id,
                event_type=event_type,
                occurred_at=when,
            )
        )
        await self.db.commit()
        return participant

    async def transition(self, session_id: UUID, target: SessionStatus) -> InterviewSession:
        item = await self.db.scalar(
            select(InterviewSession).where(InterviewSession.id == session_id).with_for_update()
        )
        if item is None:
            raise ServiceError(
                code="session_not_found", message="Interview session was not found", status_code=404
            )
        allowed = {
            SessionStatus.READY: {
                SessionStatus.IN_PROGRESS,
                SessionStatus.CANDIDATE_NO_SHOW,
                SessionStatus.INTERVIEWER_NO_SHOW,
                SessionStatus.TECHNICAL_FAILURE,
                SessionStatus.CANCELLED,
            },
            SessionStatus.IN_PROGRESS: {SessionStatus.COMPLETED, SessionStatus.TECHNICAL_FAILURE},
        }
        if target not in allowed.get(item.status, set()):
            raise ServiceError(
                code="invalid_session_transition",
                message="Interview session transition is invalid",
                status_code=409,
            )
        item.status = target
        now = datetime.now(UTC)
        event = {
            SessionStatus.IN_PROGRESS: INTERVIEW_STARTED,
            SessionStatus.COMPLETED: INTERVIEW_COMPLETED,
            SessionStatus.CANDIDATE_NO_SHOW: CANDIDATE_NO_SHOW,
            SessionStatus.INTERVIEWER_NO_SHOW: INTERVIEWER_NO_SHOW,
            SessionStatus.TECHNICAL_FAILURE: TECHNICAL_FAILURE,
        }.get(target)
        if target in {SessionStatus.COMPLETED, SessionStatus.TECHNICAL_FAILURE}:
            item.actual_end = now
            if item.actual_start:
                item.total_duration_seconds = max(0, int((now - item.actual_start).total_seconds()))
        if target is SessionStatus.IN_PROGRESS:
            item.actual_start = now
        if event:
            self._event(event, item)
        if target is SessionStatus.COMPLETED:
            item.status = SessionStatus.FEEDBACK_PENDING
        await self.db.commit()
        return item

    async def submit_feedback(
        self, session_id: UUID, interviewer_id: UUID, data: FeedbackCreate
    ) -> FeedbackReport:
        item = await self.db.get(InterviewSession, session_id)
        if item is None:
            raise ServiceError(
                code="session_not_found", message="Interview session was not found", status_code=404
            )
        if item.interviewer_id != interviewer_id:
            raise ServiceError(
                code="feedback_access_denied",
                message="Only the assigned interviewer can submit feedback",
                status_code=403,
            )
        if item.status is not SessionStatus.FEEDBACK_PENDING:
            raise ServiceError(
                code="session_not_completed",
                message="Feedback requires a completed interview",
                status_code=409,
            )
        existing = await self.db.scalar(
            select(FeedbackReport).where(FeedbackReport.session_id == session_id)
        )
        if existing:
            return existing
        rubric = await self.db.get(Rubric, item.rubric_id)
        assert rubric
        definitions = {str(x["key"]): cast(int, x["maximum_score"]) for x in rubric.criteria}
        scores = {x.key: x.score for x in data.criterion_scores}
        if set(scores) != set(definitions) or any(scores[k] > definitions[k] for k in scores):
            raise ServiceError(
                code="invalid_feedback_scores",
                message="Feedback scores do not match the rubric",
                status_code=422,
            )
        report = FeedbackReport(
            session_id=item.id,
            interviewer_id=interviewer_id,
            criterion_scores=[x.model_dump() for x in data.criterion_scores],
            strengths=data.strengths,
            improvement_areas=data.improvement_areas,
            summary=data.summary,
            readiness_level=data.readiness_level,
            total_score=sum(scores.values()),
        )
        self.db.add(report)
        await self.db.flush()
        item.status = SessionStatus.FEEDBACK_SUBMITTED
        self._event(FEEDBACK_SUBMITTED, item, {"feedback_id": str(report.id)})
        await self.db.commit()
        return report

    async def feedback(self, session_id: UUID, candidate_id: UUID) -> FeedbackReport:
        item = await self.db.get(InterviewSession, session_id)
        if (
            item is None
            or item.candidate_id != candidate_id
            or item.status is not SessionStatus.FEEDBACK_SUBMITTED
        ):
            raise ServiceError(
                code="feedback_not_found", message="Feedback report was not found", status_code=404
            )
        report = await self.db.scalar(
            select(FeedbackReport).where(FeedbackReport.session_id == session_id)
        )
        if report is None:
            raise ServiceError(
                code="feedback_not_found", message="Feedback report was not found", status_code=404
            )
        return report

    def _event(
        self, event_type: str, item: InterviewSession, extra: dict[str, object] | None = None
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(item.id),
            "booking_id": str(item.booking_id),
            "candidate_id": str(item.candidate_id),
            "interviewer_id": str(item.interviewer_id),
        }
        payload.update(extra or {})
        self.db.add(
            OutboxEvent(event_type=event_type, correlation_id=get_correlation_id(), payload=payload)
        )
