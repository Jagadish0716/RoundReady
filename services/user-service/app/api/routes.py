import hashlib
import io
import zipfile
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from app.api.schemas import (
    CandidateProfileResponse,
    NotificationDestinationResponse,
    ProfileUpsertRequest,
    ResumeMetadataResponse,
    ResumeMetadataUpsertRequest,
)
from app.application.profile_service import ProfileService
from app.dependencies import (
    AdminIdentity,
    CandidateIdentity,
    DatabaseSession,
    InternalService,
    ResumeStorageDependency,
)
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from roundready_common.errors import ServiceError

router = APIRouter(prefix="/v1", tags=["candidate profiles"])
MAX_RESUME_BYTES = 5 * 1024 * 1024
RESUME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def own_profile_response(profile: object, email: str) -> CandidateProfileResponse:
    return CandidateProfileResponse.model_validate(profile).model_copy(update={"email": email})


def validate_resume(filename: str, content_type: str, content: bytes) -> tuple[str, str]:
    safe_name = Path(filename).name
    extension = Path(safe_name).suffix.lower()
    expected_type = RESUME_TYPES.get(extension)
    if not safe_name or expected_type is None or content_type != expected_type:
        raise ServiceError(
            code="unsupported_resume_type",
            message="Resume must be a PDF, DOC, or DOCX file",
            status_code=422,
        )
    valid_signature = False
    if extension == ".pdf":
        valid_signature = content.startswith(b"%PDF-")
    elif extension == ".doc":
        valid_signature = content.startswith(bytes.fromhex("D0CF11E0A1B11AE1"))
    elif extension == ".docx" and content.startswith(b"PK"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                names = set(archive.namelist())
                valid_signature = "[Content_Types].xml" in names and any(
                    name.startswith("word/") for name in names
                )
        except zipfile.BadZipFile:
            valid_signature = False
    if not valid_signature:
        raise ServiceError(
            code="invalid_resume_content",
            message="Resume content does not match its file type",
            status_code=422,
        )
    return safe_name, extension


@router.get("/me/profile", response_model=CandidateProfileResponse)
async def get_my_profile(
    identity: CandidateIdentity, session: DatabaseSession
) -> CandidateProfileResponse:
    profile = await ProfileService(session).get_profile(identity.user_id)
    return own_profile_response(profile, identity.email)


@router.put("/me/profile", response_model=CandidateProfileResponse)
async def upsert_my_profile(
    request: ProfileUpsertRequest,
    identity: CandidateIdentity,
    session: DatabaseSession,
) -> CandidateProfileResponse:
    profile = await ProfileService(session).upsert_profile(
        identity.user_id, identity.email, request
    )
    return own_profile_response(profile, identity.email)


@router.get("/me/resume", response_model=ResumeMetadataResponse)
async def get_my_resume(
    identity: CandidateIdentity, session: DatabaseSession
) -> ResumeMetadataResponse:
    metadata = await ProfileService(session).get_resume_metadata(identity.user_id)
    return ResumeMetadataResponse.model_validate(metadata)


@router.post("/me/resume", response_model=ResumeMetadataResponse)
async def upload_my_resume(
    resume: Annotated[UploadFile, File()],
    identity: CandidateIdentity,
    session: DatabaseSession,
    storage: ResumeStorageDependency,
) -> ResumeMetadataResponse:
    await ProfileService(session).get_profile(identity.user_id)
    content = await resume.read(MAX_RESUME_BYTES + 1)
    await resume.close()
    if len(content) > MAX_RESUME_BYTES:
        raise ServiceError(
            code="resume_too_large",
            message="Resume must be 5 MB or smaller",
            status_code=413,
        )
    safe_name, extension = validate_resume(
        resume.filename or "", resume.content_type or "", content
    )
    object_key = f"{uuid4()}{extension}"
    stored = await storage.put(object_key, content)
    metadata = await ProfileService(session).upsert_resume_metadata(
        identity.user_id,
        ResumeMetadataUpsertRequest(
            storage_url=f"local://{stored.object_key}",
            file_name=safe_name,
            content_type=resume.content_type or "",
            size_bytes=len(content),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
        ),
    )
    return ResumeMetadataResponse.model_validate(metadata)


@router.get("/me/resume/content", response_class=FileResponse)
async def download_my_resume(
    identity: CandidateIdentity,
    session: DatabaseSession,
    storage: ResumeStorageDependency,
) -> FileResponse:
    metadata = await ProfileService(session).get_resume_metadata(identity.user_id)
    if not metadata.storage_url.startswith("local://"):
        raise ServiceError(
            code="resume_content_unavailable",
            message="Stored resume content is unavailable",
            status_code=404,
        )
    try:
        path = await storage.resolve(metadata.storage_url.removeprefix("local://"))
    except (FileNotFoundError, ValueError) as exc:
        raise ServiceError(
            code="resume_content_unavailable",
            message="Stored resume content is unavailable",
            status_code=404,
        ) from exc
    return FileResponse(path, media_type=metadata.content_type, filename=metadata.file_name)


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
