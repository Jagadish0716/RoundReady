from uuid import UUID

from app.api.schemas import (
    BlockoutCreateRequest,
    BlockoutResponse,
    ProfileResponse,
    ProfileUpsertRequest,
    RejectionRequest,
    SkillReplaceRequest,
    SkillResponse,
    SuspensionRequest,
    WeeklyRuleResponse,
    WeeklyRulesReplaceRequest,
)
from app.application.interviewer_service import InterviewerService
from app.dependencies import AdminIdentity, DatabaseSession, InterviewerIdentity
from app.domain.models import VerificationStatus
from fastapi import APIRouter, Response, status

router = APIRouter(prefix="/v1", tags=["interviewers"])


@router.get("/me/profile", response_model=ProfileResponse)
async def get_profile(identity: InterviewerIdentity, session: DatabaseSession) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).get_profile(identity.user_id)
    )


@router.put("/me/profile", response_model=ProfileResponse)
async def put_profile(
    request: ProfileUpsertRequest, identity: InterviewerIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).upsert_profile(identity.user_id, request)
    )


@router.post("/me/verification/submit", response_model=ProfileResponse)
async def submit_verification(
    identity: InterviewerIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).submit_verification(identity.user_id)
    )


@router.get("/me/skills", response_model=list[SkillResponse])
async def get_skills(
    identity: InterviewerIdentity, session: DatabaseSession
) -> list[SkillResponse]:
    return [
        SkillResponse.model_validate(item)
        for item in await InterviewerService(session).list_skills(identity.user_id)
    ]


@router.put("/me/skills", response_model=list[SkillResponse])
async def put_skills(
    request: SkillReplaceRequest, identity: InterviewerIdentity, session: DatabaseSession
) -> list[SkillResponse]:
    return [
        SkillResponse.model_validate(item)
        for item in await InterviewerService(session).replace_skills(identity.user_id, request)
    ]


@router.get("/me/availability/weekly", response_model=list[WeeklyRuleResponse])
async def get_weekly(
    identity: InterviewerIdentity, session: DatabaseSession
) -> list[WeeklyRuleResponse]:
    return [
        WeeklyRuleResponse.model_validate(item)
        for item in await InterviewerService(session).list_weekly_rules(identity.user_id)
    ]


@router.put("/me/availability/weekly", response_model=list[WeeklyRuleResponse])
async def put_weekly(
    request: WeeklyRulesReplaceRequest, identity: InterviewerIdentity, session: DatabaseSession
) -> list[WeeklyRuleResponse]:
    return [
        WeeklyRuleResponse.model_validate(item)
        for item in await InterviewerService(session).replace_weekly_rules(
            identity.user_id, request
        )
    ]


@router.get("/me/availability/blockouts", response_model=list[BlockoutResponse])
async def get_blockouts(
    identity: InterviewerIdentity, session: DatabaseSession
) -> list[BlockoutResponse]:
    return [
        BlockoutResponse.model_validate(item)
        for item in await InterviewerService(session).list_blockouts(identity.user_id)
    ]


@router.post("/me/availability/blockouts", response_model=BlockoutResponse, status_code=201)
async def create_blockout(
    request: BlockoutCreateRequest, identity: InterviewerIdentity, session: DatabaseSession
) -> BlockoutResponse:
    return BlockoutResponse.model_validate(
        await InterviewerService(session).create_blockout(identity.user_id, request)
    )


@router.delete("/me/availability/blockouts/{blockout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blockout(
    blockout_id: UUID, identity: InterviewerIdentity, session: DatabaseSession
) -> Response:
    await InterviewerService(session).delete_blockout(identity.user_id, blockout_id)
    return Response(status_code=204)


@router.get("/admin/verification-queue", response_model=list[ProfileResponse])
async def verification_queue(
    _admin: AdminIdentity, session: DatabaseSession
) -> list[ProfileResponse]:
    return [
        ProfileResponse.model_validate(item)
        for item in await InterviewerService(session).verification_queue()
    ]


@router.post("/admin/interviewers/{interviewer_id}/approve", response_model=ProfileResponse)
async def approve(
    interviewer_id: UUID, admin: AdminIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).review(
            interviewer_id, admin.user_id, VerificationStatus.VERIFIED
        )
    )


@router.post("/admin/interviewers/{interviewer_id}/reject", response_model=ProfileResponse)
async def reject(
    interviewer_id: UUID, request: RejectionRequest, admin: AdminIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).review(
            interviewer_id, admin.user_id, VerificationStatus.REJECTED, request.reason
        )
    )


@router.post("/admin/interviewers/{interviewer_id}/suspend", response_model=ProfileResponse)
async def suspend(
    interviewer_id: UUID, request: SuspensionRequest, admin: AdminIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).review(
            interviewer_id, admin.user_id, VerificationStatus.SUSPENDED, request.reason
        )
    )


@router.post("/admin/interviewers/{interviewer_id}/reactivate", response_model=ProfileResponse)
async def reactivate(
    interviewer_id: UUID, admin: AdminIdentity, session: DatabaseSession
) -> ProfileResponse:
    return ProfileResponse.model_validate(
        await InterviewerService(session).reactivate(interviewer_id, admin.user_id)
    )
