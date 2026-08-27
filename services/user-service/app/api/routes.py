from uuid import UUID

from app.api.schemas import (
    CandidateProfileResponse,
    ProfileUpsertRequest,
    ResumeMetadataResponse,
    ResumeMetadataUpsertRequest,
)
from app.application.profile_service import ProfileService
from app.dependencies import AdminIdentity, CandidateIdentity, DatabaseSession
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
