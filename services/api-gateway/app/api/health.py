from fastapi import APIRouter

router = APIRouter(tags=["platform"])


@router.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", include_in_schema=False)
async def ready() -> dict[str, str]:
    return {"status": "ready"}
