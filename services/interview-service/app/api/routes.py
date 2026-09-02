from uuid import UUID

from app.api.schemas import (
    AttendanceRequest,
    AttendanceResponse,
    FeedbackCreate,
    FeedbackResponse,
    JoinResponse,
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
from app.domain.providers import ParticipantAccess
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
) -> ParticipantAccess:
    return await service(db, provider, settings).join(session_id, identity)


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
