from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from shopify_cart.middleware import (
    PROCESS_TIME_HEADER,
    REQUEST_ID_HEADER,
    RequestContextMiddleware,
)


def _build_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"msg": "pong"}

    return app


def test_request_id_is_generated_when_missing() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/ping")
    assert REQUEST_ID_HEADER in r.headers
    assert len(r.headers[REQUEST_ID_HEADER]) >= 8


def test_request_id_is_echoed_when_provided() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/ping", headers={REQUEST_ID_HEADER: "my-custom-id-123"})
    assert r.headers[REQUEST_ID_HEADER] == "my-custom-id-123"


def test_process_time_header_is_numeric() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r = c.get("/ping")
    assert PROCESS_TIME_HEADER in r.headers
    value = float(r.headers[PROCESS_TIME_HEADER])
    assert value >= 0.0


def test_two_requests_get_different_ids() -> None:
    app = _build_app()
    with TestClient(app) as c:
        r1 = c.get("/ping")
        r2 = c.get("/ping")
    assert r1.headers[REQUEST_ID_HEADER] != r2.headers[REQUEST_ID_HEADER]
