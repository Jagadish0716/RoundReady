import pytest
from app.api.schemas import ProfileUpsertRequest, ResumeMetadataUpsertRequest
from pydantic import ValidationError


def test_profile_rejects_non_e164_phone() -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(full_name="Candidate", phone="9876543210")


def test_profile_rejects_non_linkedin_host() -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(
            full_name="Candidate", linkedin_url="https://malicious.example/linkedin"
        )


def test_resume_rejects_invalid_checksum_and_type() -> None:
    with pytest.raises(ValidationError):
        ResumeMetadataUpsertRequest(
            storage_url="https://documents.example.in/resume.exe",
            file_name="resume.exe",
            content_type="application/octet-stream",
            size_bytes=100,
            checksum_sha256="invalid",
        )
