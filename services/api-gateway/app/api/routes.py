from app.dependencies import require_bearer_token
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/v1")


@router.get("/session", dependencies=[Depends(require_bearer_token)])
async def session_boundary() -> dict[str, str]:
    """Proves the authentication boundary; proxy routes are added per API contract."""
    return {"status": "authenticated"}
