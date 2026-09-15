from uuid import UUID

from app.api.schemas import (
    AttendanceRequest,
    AttendanceResponse,
    FeedbackCreate,
    FeedbackResponse,
    JoinResponse,
    LocalAttendanceRequest,
    RubricCreate,
    RubricResponse,
    SessionCreate,
    SessionResponse,
    TransitionRequest,
)
from app.application.interview_service import InterviewService
from app.dependencies import (
    AdminIdentity,
    AppSettings,
    AuthenticatedIdentity,
    DatabaseSession,
    Provider,
    Role,
)
from app.domain.models import (
    FeedbackReport,
    InterviewSession,
    ParticipantAttendance,
    Rubric,
    SessionStatus,
)
from fastapi import APIRouter
from roundready_common.errors import ServiceError

router = APIRouter(prefix="/v1", tags=["interviews"])


def service(db: DatabaseSession, provider: Provider, settings: AppSettings) -> InterviewService:
    return InterviewService(db, provider, settings)


@router.post("/admin/rubrics", response_model=RubricResponse, status_code=201)
async def create_rubric(
    data: RubricCreate,
    _admin: AdminIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> Rubric:
    return await service(db, provider, settings).create_rubric(data)


@router.post("/internal/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate,
    _admin: AdminIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> InterviewSession:
    return await service(db, provider, settings).create_session(data)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> InterviewSession:
    return await service(db, provider, settings).get_session(session_id, identity)


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> list[InterviewSession]:
    return await service(db, provider, settings).list_sessions(identity)


@router.get("/sessions/{session_id}/rubric", response_model=RubricResponse)
async def get_session_rubric(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> Rubric:
    return await service(db, provider, settings).get_rubric_for_session(session_id, identity)


@router.post("/sessions/{session_id}/join", response_model=JoinResponse)
async def join(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> JoinResponse:
    access = await service(db, provider, settings).join(session_id, identity)
    return JoinResponse(
        token=access.token,
        expires_at=access.expires_at,
        join_url=access.join_url,
        provider=provider.name,
    )


@router.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> InterviewSession:
    if identity.role is not Role.INTERVIEWER:
        raise ServiceError(
            code="interviewer_role_required",
            message="Interviewer role is required",
            status_code=403,
        )
    return await service(db, provider, settings).transition_by_interviewer(
        session_id, identity.user_id, SessionStatus.IN_PROGRESS
    )


@router.post("/sessions/{session_id}/complete", response_model=SessionResponse)
async def complete(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> InterviewSession:
    if identity.role is not Role.INTERVIEWER:
        raise ServiceError(
            code="interviewer_role_required",
            message="Interviewer role is required",
            status_code=403,
        )
    return await service(db, provider, settings).transition_by_interviewer(
        session_id, identity.user_id, SessionStatus.COMPLETED
    )


@router.post("/internal/sessions/{session_id}/attendance", response_model=AttendanceResponse)
async def attendance(
    session_id: UUID,
    data: AttendanceRequest,
    _admin: AdminIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> ParticipantAttendance:
    return await service(db, provider, settings).attendance(
        session_id, data.provider_event_id, data.user_id, data.event_type, data.occurred_at
    )


@router.post("/admin/sessions/{session_id}/transition", response_model=SessionResponse)
async def transition(
    session_id: UUID,
    data: TransitionRequest,
    _admin: AdminIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> InterviewSession:
    return await service(db, provider, settings).transition(session_id, data.status)


@router.post("/sessions/{session_id}/feedback", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    session_id: UUID,
    data: FeedbackCreate,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> FeedbackReport:
    if identity.role is not Role.INTERVIEWER:
        raise ServiceError(
            code="interviewer_role_required",
            message="Interviewer role is required",
            status_code=403,
        )
    return await service(db, provider, settings).submit_feedback(session_id, identity.user_id, data)


@router.get("/sessions/{session_id}/feedback", response_model=FeedbackResponse)
async def feedback(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> FeedbackReport:
    if identity.role is not Role.CANDIDATE:
        raise ServiceError(
            code="candidate_role_required", message="Candidate role is required", status_code=403
        )
    return await service(db, provider, settings).feedback(session_id, identity.user_id)


@router.post("/internal/rubrics/default", response_model=RubricResponse)
async def default_rubric(_admin: AdminIdentity, db: DatabaseSession) -> Rubric:
    from uuid import NAMESPACE_URL, uuid5

    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    rubric_id = uuid5(NAMESPACE_URL, "roundready:general-interview-rubric:v1")
    await db.execute(
        insert(Rubric)
        .values(
            id=rubric_id,
            domain="general",
            topic="professional_skills",
            experience_level="all",
            version=1,
            maximum_score=30,
            active=True,
            criteria=[
                {
                    "key": "technical",
                    "label": "Technical understanding",
                    "weight": 40,
                    "maximum_score": 10,
                },
                {
                    "key": "problem_solving",
                    "label": "Problem solving",
                    "weight": 40,
                    "maximum_score": 10,
                },
                {
                    "key": "communication",
                    "label": "Communication",
                    "weight": 20,
                    "maximum_score": 10,
                },
            ],
        )
        .on_conflict_do_nothing()
    )
    await db.commit()
    rubric = await db.scalar(
        select(Rubric).where(
            Rubric.domain == "general",
            Rubric.topic == "professional_skills",
            Rubric.experience_level == "all",
            Rubric.version == 1,
        )
    )
    assert rubric is not None
    return rubric


@router.get("/sessions/{session_id}/attendance", response_model=list[AttendanceResponse])
async def participant_attendance(
    session_id: UUID,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> list[ParticipantAttendance]:
    from sqlalchemy import select

    await service(db, provider, settings).get_session(session_id, identity)
    return list(
        (
            await db.scalars(
                select(ParticipantAttendance).where(ParticipantAttendance.session_id == session_id)
            )
        ).all()
    )


@router.post("/sessions/{session_id}/development/attendance", response_model=AttendanceResponse)
async def local_attendance(
    session_id: UUID,
    data: LocalAttendanceRequest,
    identity: AuthenticatedIdentity,
    db: DatabaseSession,
    provider: Provider,
    settings: AppSettings,
) -> ParticipantAttendance:
    from datetime import UTC, datetime
    from uuid import uuid4

    if (
        settings.environment not in {"development", "test"}
        or settings.video_provider != "development"
    ):
        raise ServiceError(
            code="development_room_disabled", message="Local room is unavailable", status_code=404
        )
    application = service(db, provider, settings)
    # Enforce participant identity, lifecycle and scheduled access window through normal join.
    await application.join(session_id, identity)
    return await application.attendance(
        session_id, f"local-{uuid4()}", identity.user_id, data.event_type, datetime.now(UTC)
    )
