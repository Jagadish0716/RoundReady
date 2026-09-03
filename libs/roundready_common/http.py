from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from roundready_common.correlation import get_correlation_id
from roundready_common.errors import ApiError, ErrorDetail, ServiceError


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def service_error_handler(_request: Request, exc: ServiceError) -> JSONResponse:
        body = ApiError(
            error=ErrorDetail(code=exc.code, message=exc.message, details=exc.details),
            correlation_id=get_correlation_id(),
        )
        headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
        return JSONResponse(
            status_code=exc.status_code,
            content=body.model_dump(mode="json"),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        body = ApiError(
            error=ErrorDetail(
                code="validation_error",
                message="Request validation failed",
                details={
                    "errors": [
                        {
                            "type": error.get("type"),
                            "loc": error.get("loc"),
                            "msg": error.get("msg"),
                        }
                        for error in exc.errors()
                    ]
                },
            ),
            correlation_id=get_correlation_id(),
        )
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))
