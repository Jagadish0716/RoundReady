from uuid import UUID

from app.api.schemas import ProfileUpsertRequest, ResumeMetadataUpsertRequest
from app.domain.models import CandidateProfile, ResumeMetadata, utc_now
from roundready_common.errors import ServiceError
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: UUID) -> CandidateProfile:
        profile = await self._session.get(CandidateProfile, user_id)
        if profile is None:
            raise ServiceError(
                code="candidate_profile_not_found",
                message="Candidate profile was not found",
                status_code=404,
            )
        return profile

    async def upsert_profile(
        self, user_id: UUID, request: ProfileUpsertRequest
    ) -> CandidateProfile:
        values = request.model_dump(mode="json")
        values["user_id"] = user_id
        update_values = {key: value for key, value in values.items() if key != "user_id"}
        update_values["updated_at"] = utc_now()
        statement = (
            insert(CandidateProfile)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[CandidateProfile.user_id],
                set_=update_values,
            )
            .returning(CandidateProfile)
        )
        result = await self._session.execute(statement)
        await self._session.commit()
        return result.scalar_one()

    async def get_resume_metadata(self, user_id: UUID) -> ResumeMetadata:
        metadata = await self._session.get(ResumeMetadata, user_id)
        if metadata is None:
            raise ServiceError(
                code="resume_metadata_not_found",
                message="Resume metadata was not found",
                status_code=404,
            )
        return metadata

    async def upsert_resume_metadata(
        self, user_id: UUID, request: ResumeMetadataUpsertRequest
    ) -> ResumeMetadata:
        profile_exists = await self._session.scalar(
            select(CandidateProfile.user_id).where(CandidateProfile.user_id == user_id)
        )
        if profile_exists is None:
            raise ServiceError(
                code="candidate_profile_required",
                message="Create the candidate profile before adding resume metadata",
                status_code=409,
            )
        values = request.model_dump(mode="json")
        values["user_id"] = user_id
        update_values = {key: value for key, value in values.items() if key != "user_id"}
        update_values["updated_at"] = utc_now()
        statement = (
            insert(ResumeMetadata)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[ResumeMetadata.user_id],
                set_=update_values,
            )
            .returning(ResumeMetadata)
        )
        result = await self._session.execute(statement)
        await self._session.commit()
        return result.scalar_one()
