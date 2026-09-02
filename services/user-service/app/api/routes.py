from uuid import UUID

from app.api.schemas import (
    CandidateProfileResponse,
    NotificationDestinationResponse,
    ProfileUpsertRequest,
    ResumeMetadataResponse,
    ResumeMetadataUpsertRequest,
)
from app.application.profile_service import ProfileService
from app.dependencies import AdminIdentity, CandidateIdentity, DatabaseSession, InternalService
from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["candidate profiles"])


@router.get("/me/profile", response_model=CandidateProfileResponse)
async def get_my_profile(
    identity: CandidateIdentity, session: DatabaseSession
) -> CandidateProfileResponse:
    profile = await ProfileService(session).get_profile(identity.user_id)
    return CandidateProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=CandidateProfileResponse)
async def upsert_my_profile(
    request: ProfileUpsertRequest,
    identity: CandidateIdentity,
    session: DatabaseSession,
) -> CandidateProfileResponse:
    profile = await ProfileService(session).upsert_profile(identity.user_id, request)
    return CandidateProfileResponse.model_validate(profile)


@router.get("/me/resume", response_model=ResumeMetadataResponse)
async def get_my_resume(
    identity: CandidateIdentity, session: DatabaseSession
) -> ResumeMetadataResponse:
    metadata = await ProfileService(session).get_resume_metadata(identity.user_id)
    return ResumeMetadataResponse.model_validate(metadata)


@router.put("/me/resume", response_model=ResumeMetadataResponse)
async def upsert_my_resume(
    request: ResumeMetadataUpsertRequest,
    identity: CandidateIdentity,
    session: DatabaseSession,
) -> ResumeMetadataResponse:
    metadata = await ProfileService(session).upsert_resume_metadata(identity.user_id, request)
    return ResumeMetadataResponse.model_validate(metadata)


@router.get("/admin/candidates/{user_id}", response_model=CandidateProfileResponse)
async def admin_get_candidate(
    user_id: UUID, _admin: AdminIdentity, session: DatabaseSession
) -> CandidateProfileResponse:
    profile = await ProfileService(session).get_profile(user_id)
    return CandidateProfileResponse.model_validate(profile)


@router.get(
    "/internal/candidates/{user_id}/notification-destination",
    response_model=NotificationDestinationResponse,
)
async def notification_destination(
    user_id: UUID, _service: InternalService, session: DatabaseSession
) -> NotificationDestinationResponse:
    profile = await ProfileService(session).get_profile(user_id)
    return NotificationDestinationResponse(
        user_id=user_id, email=profile.email, phone=profile.phone
    )
