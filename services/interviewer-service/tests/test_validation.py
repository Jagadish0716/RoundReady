import pytest
from app.api.schemas import WeeklyRulesReplaceRequest
from pydantic import ValidationError


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
