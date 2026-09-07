import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def test_layered_verification_migration_up_down_up(postgres_url: str) -> None:
    os.environ["INTERVIEWER_DATABASE_URL"] = postgres_url.replace(
        "postgresql+psycopg", "postgresql+asyncpg"
    )
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    command.downgrade(config, "0001_interviewer")
    command.upgrade(config, "head")
