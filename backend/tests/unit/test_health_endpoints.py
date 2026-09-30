from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_db_endpoint_returns_json(client: TestClient) -> None:
    r = client.get("/health/db")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in {"ok", "error"}
    assert "database" in body


def test_health_kafka_endpoint_returns_json(client: TestClient) -> None:
    r = client.get("/health/kafka")
    assert r.status_code == 200
    body = r.json()
    # In tests KAFKA_ENABLED=false → status=error, kafka=not_connected
    assert body["status"] in {"ok", "error"}
    assert "kafka" in body
