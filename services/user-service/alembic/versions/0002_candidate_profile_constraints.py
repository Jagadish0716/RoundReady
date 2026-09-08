"""Constrain candidate experience and preferred language.

Revision ID: 0002_profile_constraints
Revises: 0001_candidate_profiles
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_profile_constraints"
down_revision: str | None = "0001_candidate_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE candidate_profiles SET experience_years = 20 WHERE experience_years > 20")
    op.execute(
        "UPDATE candidate_profiles SET preferred_language = CASE "
        "WHEN lower(trim(preferred_language)) = 'hindi' THEN 'Hindi' "
        "WHEN lower(trim(preferred_language)) = 'kannada' THEN 'Kannada' "
        "WHEN lower(trim(preferred_language)) = 'tamil' THEN 'Tamil' "
        "WHEN lower(trim(preferred_language)) = 'telugu' THEN 'Telugu' "
        "WHEN lower(trim(preferred_language)) = 'malayalam' THEN 'Malayalam' "
        "WHEN lower(trim(preferred_language)) = 'marathi' THEN 'Marathi' "
        "WHEN lower(trim(preferred_language)) = 'bengali' THEN 'Bengali' "
        "ELSE 'English' END"
    )
    op.drop_constraint(
        "ck_candidate_profiles_experience_years", "candidate_profiles", type_="check"
    )
    op.create_check_constraint(
        "ck_candidate_profiles_experience_years",
        "candidate_profiles",
        "experience_years >= 0 AND experience_years <= 20",
    )
    op.create_check_constraint(
        "ck_candidate_profiles_preferred_language",
        "candidate_profiles",
        "preferred_language IN ('English', 'Hindi', 'Kannada', 'Tamil', 'Telugu', "
        "'Malayalam', 'Marathi', 'Bengali')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_candidate_profiles_preferred_language", "candidate_profiles", type_="check"
    )
    op.drop_constraint(
        "ck_candidate_profiles_experience_years", "candidate_profiles", type_="check"
    )
    op.create_check_constraint(
        "ck_candidate_profiles_experience_years",
        "candidate_profiles",
        "experience_years >= 0 AND experience_years <= 60",
    )
