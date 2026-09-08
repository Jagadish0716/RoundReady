from copy import deepcopy

import pytest
from app.api.schemas import ProfileUpsertRequest, WeeklyRulesReplaceRequest
from pydantic import ValidationError

VALID_PROFILE = {
    "full_name": "Ana María O'Neil",
    "headline": "Cloud Architect",
    "company": "Independent",
    "job_title": "Principal Engineer",
    "experience_years": "15.5",
    "linkedin_url": "https://www.linkedin.com/in/ana-oneil",
    "github_url": "https://github.com/ana-oneil",
    "bio": "I mentor engineers through practical cloud architecture and system design interviews.",
}


def test_profile_trims_valid_full_name() -> None:
    profile = ProfileUpsertRequest(**{**VALID_PROFILE, "full_name": "  Ana María O'Neil  "})
    assert profile.full_name == "Ana María O'Neil"


@pytest.mark.parametrize("full_name", ["", " ", "A", "x" * 101])
def test_profile_rejects_invalid_full_name(full_name: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(**{**VALID_PROFILE, "full_name": full_name})


@pytest.mark.parametrize(
    "field",
    [
        "full_name",
        "headline",
        "company",
        "job_title",
        "experience_years",
        "linkedin_url",
        "github_url",
        "bio",
    ],
)
def test_profile_rejects_each_missing_required_field(field: str) -> None:
    payload = deepcopy(VALID_PROFILE)
    payload.pop(field)
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(**payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("experience_years", "60.1"),
        ("experience_years", "1.55"),
        ("linkedin_url", "https://www.linkedin.com/not-a-profile"),
        ("github_url", "https://github.com/user/repository"),
        ("bio", "Too short"),
    ],
)
def test_profile_rejects_invalid_required_values(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        ProfileUpsertRequest(**{**VALID_PROFILE, field: value})


def test_invalid_timezone_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WeeklyRulesReplaceRequest(
            rules=[
                {
                    "weekday": 1,
                    "start_time": "09:00",
                    "end_time": "10:00",
                    "timezone": "Invalid/Zone",
                }
            ]
        )


def test_overlapping_weekly_rules_are_rejected() -> None:
    with pytest.raises(ValidationError):
        WeeklyRulesReplaceRequest(
            rules=[
                {
                    "weekday": 1,
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "timezone": "Asia/Kolkata",
                },
                {
                    "weekday": 1,
                    "start_time": "10:00",
                    "end_time": "12:00",
                    "timezone": "Asia/Kolkata",
                },
            ]
        )
