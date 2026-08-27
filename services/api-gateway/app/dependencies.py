from typing import Annotated

from fastapi import Header
from roundready_common.errors import ServiceError


async def require_bearer_token(authorization: Annotated[str | None, Header()] = None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise ServiceError(code="unauthorized", message="Bearer token required", status_code=401)
    return authorization.removeprefix("Bearer ")
