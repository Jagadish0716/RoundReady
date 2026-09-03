from dataclasses import dataclass
from typing import Annotated

import httpx
from app.config import Settings, get_settings
from app.dependencies import HttpClient, Identity, Limiter, Role, authenticate
from fastapi import APIRouter, Depends, Request, Response
from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ServiceError

router = APIRouter()


@dataclass(frozen=True)
class RouteTarget:
    prefix: str
    service_url_attribute: str
    downstream_prefix: str


ROUTES = (
    RouteTarget("v1/auth", "auth_service_url", "/v1/auth"),
    RouteTarget("v1/users", "user_service_url", "/v1"),
    RouteTarget("v1/interviewers", "interviewer_service_url", "/v1"),
    RouteTarget("v1/booking", "booking_service_url", "/v1"),
    RouteTarget("v1/payments", "payment_service_url", "/v1/payments"),
    RouteTarget("v1/interviews", "interview_service_url", "/v1"),
    RouteTarget("v1/notifications", "notification_service_url", "/v1/notifications"),
)
PUBLIC_PATHS = {
    ("POST", "v1/auth/register"),
    ("POST", "v1/auth/login"),
    ("POST", "v1/auth/refresh"),
    ("POST", "v1/payments/webhooks/razorpay"),
}


def _role_required(method: str, path: str) -> Role | None:
    if "/admin/" in f"/{path}/" or path.endswith("/admin"):
        return Role.ADMIN
    if path.startswith("v1/users/me/"):
        return Role.CANDIDATE
    if path.startswith("v1/interviewers/me/"):
        return Role.INTERVIEWER
    if (
        method == "POST"
        and path.startswith("v1/interviews/sessions/")
        and path.endswith("/feedback")
    ):
        return Role.INTERVIEWER
    return None


def _resolve(path: str, settings: Settings) -> tuple[str, str]:
    if path == "v1/payments/webhooks/razorpay":
        return str(settings.payment_service_url).rstrip("/"), "/v1/webhooks/razorpay"
    for target in ROUTES:
        if path == target.prefix or path.startswith(f"{target.prefix}/"):
            suffix = path[len(target.prefix) :]
            base = str(getattr(settings, target.service_url_attribute)).rstrip("/")
            return base, f"{target.downstream_prefix}{suffix}"
    raise ServiceError(code="route_not_found", message="API route was not found", status_code=404)


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def proxy(
    path: str,
    request: Request,
    client: HttpClient,
    limiter: Limiter,
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    if "/internal/" in f"/{path}/":
        raise ServiceError(
            code="route_not_found", message="API route was not found", status_code=404
        )
    method = request.method.upper()
    public = (method, path) in PUBLIC_PATHS
    identity: Identity | None = None
    if not public:
        authorization = request.headers.get("Authorization")
        identity = await authenticate(settings, client, authorization)
        required = _role_required(method, path)
        if required is not None and identity.role is not required:
            raise ServiceError(
                code="insufficient_permissions",
                message="The authenticated role cannot access this resource",
                status_code=403,
            )
    remote = request.client.host if request.client else "unknown"
    rate_key = str(identity.user_id) if identity else remote
    limit = settings.rate_limit_requests
    window = settings.rate_limit_window_seconds
    if public and path in {"v1/auth/login", "v1/auth/register", "v1/auth/refresh"}:
        rate_key = f"auth:{path}:{rate_key}"
        limit = settings.auth_rate_limit_requests
        window = settings.auth_rate_limit_window_seconds
    if not await limiter.allow(rate_key, limit, window):
        raise ServiceError(code="rate_limit_exceeded", message="Too many requests", status_code=429)
    base_url, downstream_path = _resolve(path, settings)
    headers: dict[str, str] = {"X-Correlation-ID": get_correlation_id()}
    for name in (
        "content-type",
        "accept",
        "idempotency-key",
        "x-razorpay-signature",
        "x-razorpay-event-id",
    ):
        value = request.headers.get(name)
        if value is not None:
            headers[name] = value
    authorization = request.headers.get("Authorization")
    if authorization and path.startswith("v1/auth"):
        headers["Authorization"] = authorization
    if identity:
        identity_secret = settings.internal_identity_secret.get_secret_value()
        if path.startswith("v1/notifications"):
            identity_secret = (
                settings.notification_internal_identity_secret.get_secret_value() or identity_secret
            )
        headers.update(
            {
                "X-User-ID": str(identity.user_id),
                "X-User-Role": identity.role.value,
                "X-Internal-Identity-Secret": identity_secret,
            }
        )
    try:
        upstream = await client.request(
            method,
            f"{base_url}{downstream_path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise ServiceError(
            code="downstream_service_unavailable",
            message="Downstream service is unavailable",
            status_code=503,
        ) from exc
    if upstream.status_code >= 500:
        raise ServiceError(
            code="downstream_service_error",
            message="Downstream service failed",
            status_code=502,
        )
    response_headers: dict[str, str] = {}
    for name in ("content-type", "www-authenticate"):
        if name in upstream.headers:
            response_headers[name] = upstream.headers[name]
    return Response(
        content=upstream.content, status_code=upstream.status_code, headers=response_headers
    )
