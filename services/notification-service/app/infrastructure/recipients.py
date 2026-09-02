import httpx
from app.domain.providers import NotificationDestination


class UserServiceRecipientResolver:
    def __init__(self, base_url: str, secret: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._secret = secret

    async def resolve(self, user_id: str, correlation_id: str) -> NotificationDestination:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(
                f"{self._base_url}/v1/internal/candidates/{user_id}/notification-destination",
                headers={
                    "X-Service-Name": "notification-service",
                    "X-Internal-Service-Secret": self._secret,
                    "X-Correlation-ID": correlation_id,
                },
            )
        response.raise_for_status()
        data = response.json()
        return NotificationDestination(email=data.get("email"), phone=data.get("phone"))
