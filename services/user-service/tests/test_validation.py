from decimal import Decimal

import pytest
from app.api.schemas import ProfileUpsertRequest, ResumeMetadataUpsertRequest
from pydantic import ValidationError


def test_profile_rejects_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(full_name="Candidate", phone="not-a-number")


@pytest.mark.parametrize(
    "phone", ["+919876543210", "+918123456789", "+917012345678", "+916123456789"]
)
def test_profile_accepts_valid_indian_mobile_phone(phone: str) -> None:
    assert ProfileUpsertRequest(full_name="Candidate", phone=phone).phone == phone


@pytest.mark.parametrize(
    "phone", ["+911234567890", "+915123456789", "+91987654321", "+9198765432100"]
)
def test_profile_rejects_invalid_indian_mobile_phone(phone: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(full_name="Candidate", phone=phone)


@pytest.mark.parametrize("years", ["0", "0.5", "1.5", "20"])
def test_profile_accepts_experience_within_one_decimal_precision(years: str) -> None:
    assert ProfileUpsertRequest(
        full_name="Candidate", experience_years=years
    ).experience_years == Decimal(years)


@pytest.mark.parametrize("years", ["-1", "21", "99999999", "1.55", "1e5"])
def test_profile_rejects_invalid_experience(years: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(full_name="Candidate", experience_years=years)


def test_profile_rejects_non_linkedin_host() -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(
            full_name="Candidate", linkedin_url="https://malicious.example/linkedin"
        )


def test_resume_rejects_invalid_checksum_and_type() -> None:
    with pytest.raises(ValidationError):
        ResumeMetadataUpsertRequest(
            storage_url="local://resume.exe",
            file_name="resume.exe",
            content_type="application/octet-stream",
            size_bytes=100,
            checksum_sha256="invalid",
        )
