"""Application exception hierarchy + FastAPI handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shopify_cart.logging_config import get_logger

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Backward-compatible HTTP status constants
# ----------------------------------------------------------------------
# Starlette renamed HTTP_422_UNPROCESSABLE_ENTITY to
# HTTP_422_UNPROCESSABLE_CONTENT. Resolve at import time so the same
# code works on both old and new versions without deprecation warnings.
HTTP_422: int = getattr(
    status,
    "HTTP_422_UNPROCESSABLE_CONTENT",
    getattr(status, "HTTP_422_UNPROCESSABLE_ENTITY", 422),
)


# ----------------------------------------------------------------------
# App exception hierarchy
# ----------------------------------------------------------------------
class AppError(Exception):
    """Base class for all application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: Any | None = None,
    ) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.detail = detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"
    message = "Resource not found."


class ValidationError(AppError):
    status_code = HTTP_422
    error_code = "validation_error"
    message = "Validation failed."


class AuthError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "auth_error"
    message = "Authentication failed."


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "permission_denied"
    message = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    error_code = "conflict"
    message = "Resource conflict."


class CartError(AppError):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "cart_error"
    message = "Cart operation failed."


class InventoryError(AppError):
    # 409 Conflict — request is well-formed but conflicts with current
    # inventory state (e.g. insufficient stock at checkout).
    status_code = status.HTTP_409_CONFLICT
    error_code = "inventory_error"
    message = "Inventory operation failed."


class MLModelError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "ml_model_error"
    message = "ML model unavailable or prediction failed."


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _error_payload(
    *,
    error_code: str,
    message: str,
    status_code: int,
    path: str,
    detail: Any | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": error_code,
        "status": status_code,
        "detail": message,
        "path": path,
    }
    if detail is not None:
        payload["extra"] = detail
    return payload


# ----------------------------------------------------------------------
# Handlers
# ----------------------------------------------------------------------
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            error_code=exc.error_code,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                error_code=exc.error_code,
                message=exc.message,
                status_code=exc.status_code,
                path=request.url.path,
                detail=exc.detail,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(
                error_code="http_error",
                message=str(exc.detail),
                status_code=exc.status_code,
                path=request.url.path,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_422,
            content=_error_payload(
                error_code="validation_error",
                message="Request validation failed.",
                status_code=HTTP_422,
                path=request.url.path,
                detail=exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            exc_type=type(exc).__name__,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload(
                error_code="internal_error",
                message="An unexpected error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                path=request.url.path,
            ),
        )
