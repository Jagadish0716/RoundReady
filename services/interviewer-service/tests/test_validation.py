from copy import deepcopy

import pytest
from app.api.schemas import ProfileUpsertRequest, SkillReplaceRequest, WeeklyRulesReplaceRequest
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


def test_multiple_weekdays_with_iana_timezone_are_valid() -> None:
    value = WeeklyRulesReplaceRequest.model_validate(
        {
            "rules": [
                {
                    "weekday": 0,
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "timezone": "Asia/Kolkata",
                },
                {
                    "weekday": 2,
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "timezone": "Asia/Kolkata",
                },
            ]
        }
    )
    assert len(value.rules) == 2


def test_overlapping_same_day_rules_are_rejected() -> None:
    with pytest.raises(ValidationError, match="cannot overlap"):
        WeeklyRulesReplaceRequest.model_validate(
            {
                "rules": [
                    {
                        "weekday": 0,
                        "start_time": "18:00",
                        "end_time": "20:00",
                        "timezone": "Asia/Kolkata",
                    },
                    {
                        "weekday": 0,
                        "start_time": "19:00",
                        "end_time": "21:00",
                        "timezone": "Asia/Kolkata",
                    },
                ]
            }
        )


def test_non_overlapping_same_day_rules_are_valid() -> None:
    value = WeeklyRulesReplaceRequest.model_validate(
        {
            "rules": [
                {
                    "weekday": 0,
                    "start_time": "09:00",
                    "end_time": "11:00",
                    "timezone": "Europe/London",
                },
                {
                    "weekday": 0,
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "timezone": "Europe/London",
                },
            ]
        }
    )
    assert len(value.rules) == 2


def test_catalog_skills_allow_multiple_skills_with_one_domain_experience() -> None:
    value = SkillReplaceRequest.model_validate(
        {
            "skills": [
                {
                    "domain": "DevOps",
                    "topic": "docker",
                    "skill_name": "Docker",
                    "experience_years": "5.0",
                },
                {
                    "domain": "DevOps",
                    "topic": "kubernetes",
                    "skill_name": "Kubernetes",
                    "experience_years": "5.0",
                },
            ]
        }
    )
    assert len(value.skills) == 2


def test_catalog_requires_at_least_one_domain_skill() -> None:
    with pytest.raises(ValidationError):
        SkillReplaceRequest.model_validate({"skills": []})


@pytest.mark.parametrize(
    "skills",
    [
        [
            {
                "domain": "DevOps",
                "topic": "docker",
                "skill_name": "Invented",
                "experience_years": "5.0",
            }
        ],
        [
            {"domain": "AWS", "topic": "ec2", "skill_name": "EC2", "experience_years": "4.0"},
            {"domain": "AWS", "topic": "ec2", "skill_name": "EC2", "experience_years": "4.0"},
        ],
        [
            {"domain": "AWS", "topic": "ec2", "skill_name": "EC2", "experience_years": "4.0"},
            {"domain": "AWS", "topic": "s3", "skill_name": "S3", "experience_years": "5.0"},
        ],
    ],
)
def test_catalog_skills_reject_invalid_or_inconsistent_rows(skills: list[dict[str, str]]) -> None:
    with pytest.raises(ValidationError):
        SkillReplaceRequest.model_validate({"skills": skills})


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
