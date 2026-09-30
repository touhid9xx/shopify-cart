"""Integration tests for admin analytics endpoints."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shopify_cart.db.session import SessionLocal


@pytest.fixture(autouse=True)
def _require_mysql() -> None:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar()
    except SQLAlchemyError as exc:
        pytest.skip(f"MySQL not available: {exc}")


def _unique_sku() -> str:
    return f"SKU-{uuid.uuid4().hex[:8].upper()}"


def _make_admin(client: TestClient) -> dict[str, str]:
    email = f"ana-admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    with SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
        db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": uid})
        db.commit()
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_admin_can_list_daily_sales(client: TestClient) -> None:
    admin = _make_admin(client)
    r = client.get("/api/v1/admin/analytics/sales", headers=admin)
    assert r.status_code == 200
    assert "items" in r.json()


def test_admin_can_list_alerts(client: TestClient) -> None:
    admin = _make_admin(client)
    r = client.get("/api/v1/admin/analytics/alerts", headers=admin)
    assert r.status_code == 200
    assert "items" in r.json()


def test_non_admin_cannot_access_analytics(client: TestClient) -> None:
    email = f"plain-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.get("/api/v1/admin/analytics/sales", headers=headers)
    assert r.status_code == 403


def test_resolve_nonexistent_alert_returns_404(client: TestClient) -> None:
    admin = _make_admin(client)
    r = client.post("/api/v1/admin/analytics/alerts/999999/resolve", headers=admin)
    assert r.status_code == 404
