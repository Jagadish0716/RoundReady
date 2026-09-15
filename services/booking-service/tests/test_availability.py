from datetime import UTC, datetime
from uuid import uuid4

from app.application.availability import Snapshot, windows


def test_weekly_windows_preserve_indian_local_time_and_blockouts() -> None:
    snapshot = Snapshot.model_validate(
        {
            "interviewer_id": str(uuid4()),
            "verified": True,
            "deleted": False,
            "observed_at": "2026-09-10T00:00:00Z",
            "skills": [],
            "rules": [
                {
                    "weekday": 0,
                    "start_time": "18:00",
                    "end_time": "20:00",
                    "timezone": "Asia/Kolkata",
                }
            ],
            "blockouts": [{"starts_at": "2026-09-14T12:30:00Z", "ends_at": "2026-09-14T12:50:00Z"}],
        }
    )
    result = sorted(windows(snapshot, datetime(2026, 9, 10, tzinfo=UTC), 20))
    assert result[0][0] == datetime(2026, 9, 14, 12, 50, tzinfo=UTC)
    assert len(result) == 23
    assert len(result) == len(set(result))
