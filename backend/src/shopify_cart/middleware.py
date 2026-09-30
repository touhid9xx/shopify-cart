"""Request context middleware: request ID + latency + context binding."""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from shopify_cart.logging_config import get_logger

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Public constants — single source of truth for header names.
# Tests and other modules import these instead of hardcoding strings.
# ----------------------------------------------------------------------
REQUEST_ID_HEADER: str = "X-Request-ID"
PROCESS_TIME_HEADER: str = "X-Process-Time-Ms"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Adds X-Request-ID and X-Process-Time-Ms, binds log contextvars."""

    def __init__(self, app: ASGIApp, *, header_name: str = REQUEST_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(self.header_name) or uuid.uuid4().hex

        # Bind to structlog context so all logs inside this request include it.
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Log and re-raise so the exception handler still runs.
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_failed",
                duration_ms=round(duration_ms, 2),
            )
            raise
        else:
            # Success path — add headers and log.
            duration_ms = (time.perf_counter() - start) * 1000
            response.headers[self.header_name] = request_id
            response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}"

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                request_id=request_id,
            )
            return response
        finally:
            # Always runs — clean up contextvars after the request.
            structlog.contextvars.unbind_contextvars("request_id", "method", "path")
