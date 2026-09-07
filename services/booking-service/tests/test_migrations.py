import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_interviewer_eligibility_migration_up_down_up(
    infrastructure: tuple[str, str],
) -> None:
    postgres_url, _redis_url = infrastructure
    os.environ["BOOKING_DATABASE_URL"] = postgres_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "0003_reusable_failed_slots")
    command.upgrade(config, "head")
