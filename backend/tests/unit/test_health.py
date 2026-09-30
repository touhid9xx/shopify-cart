from __future__ import annotations

from fastapi.testclient import TestClient

from shopify_cart.middleware import PROCESS_TIME_HEADER, REQUEST_ID_HEADER


def test_health_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"]
    assert body["env"] == "test"


def test_health_has_request_id_header(client: TestClient) -> None:
    resp = client.get("/health")
    assert REQUEST_ID_HEADER in resp.headers
    assert len(resp.headers[REQUEST_ID_HEADER]) >= 8


def test_health_has_process_time_header(client: TestClient) -> None:
    resp = client.get("/health")
    assert PROCESS_TIME_HEADER in resp.headers
    assert float(resp.headers[PROCESS_TIME_HEADER]) >= 0.0


def test_unknown_route_returns_consistent_error_shape(client: TestClient) -> None:
    resp = client.get("/does-not-exist")
    assert resp.status_code == 404
    body = resp.json()
    assert set(body.keys()) >= {"error", "status", "detail", "path"}
    assert body["path"] == "/does-not-exist"
