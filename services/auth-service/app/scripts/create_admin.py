import argparse
import asyncio
import getpass
import os
from enum import StrEnum

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Credential, Role
from app.domain.security import hash_password


class ProvisionResult(StrEnum):
    CREATED = "created"
    ALREADY_EXISTS = "already_exists"


async def provision_admin(session: AsyncSession, email: str, password: str) -> ProvisionResult:
    normalized_email = str(validate_email(email, check_deliverability=False).normalized).lower()
    if len(password) < 12 or len(password) > 128:
        raise ValueError("password must contain between 12 and 128 characters")
    existing = await session.scalar(select(Credential).where(Credential.email == normalized_email))
    if existing is not None:
        if existing.role is not Role.ADMIN:
            raise ValueError("email already belongs to a non-admin account")
        return ProvisionResult.ALREADY_EXISTS
    session.add(
        Credential(
            email=normalized_email,
            password_hash=hash_password(password),
            role=Role.ADMIN,
        )
    )
    await session.commit()
    return ProvisionResult.CREATED


async def run(email: str, password: str) -> ProvisionResult:
    from app.infrastructure.database import session_factory

    async with session_factory() as session:
        return await provision_admin(session, email, password)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create RoundReady's initial admin account if it does not exist."
    )
    parser.add_argument("--email", default=os.getenv("ROUNDREADY_ADMIN_EMAIL"))
    arguments = parser.parse_args()
    email = arguments.email or input("Admin email: ").strip()
    password = os.getenv("ROUNDREADY_ADMIN_PASSWORD") or getpass.getpass("Admin password: ")
    try:
        result = asyncio.run(run(email, password))
    except (EmailNotValidError, ValueError) as exc:
        parser.error(str(exc))
    print(f"Admin provisioning: {result.value}")


if __name__ == "__main__":
    main()
