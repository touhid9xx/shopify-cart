"""Inventory API integration tests — require MySQL running."""

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
    email = f"inv-admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "admin12345"})
    with SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
        db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": uid})
        db.commit()
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "admin12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_inventory_created_with_product(client: TestClient) -> None:
    admin = _make_admin(client)
    created = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={"name": "P", "sku": _unique_sku(), "price": "5.00"},
    ).json()

    r = client.get(f"/api/v1/inventory/product/{created['id']}")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["quantity"] == 0
    assert rows[0]["location"] == "default"


def test_admin_can_adjust_inventory(client: TestClient) -> None:
    admin = _make_admin(client)
    created = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={"name": "P", "sku": _unique_sku(), "price": "5.00"},
    ).json()
    inv_id = client.get(f"/api/v1/inventory/product/{created['id']}").json()[0]["id"]

    r = client.patch(
        f"/api/v1/inventory/{inv_id}/adjust",
        headers=admin,
        json={"delta": 25, "reason": "restock"},
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == 25


def test_adjust_below_zero_returns_409(client: TestClient) -> None:
    """Cannot reduce stock below 0 → 409 Conflict (state conflict, not bad request)."""
    admin = _make_admin(client)
    created = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={"name": "P", "sku": _unique_sku(), "price": "5.00"},
    ).json()
    inv_id = client.get(f"/api/v1/inventory/product/{created['id']}").json()[0]["id"]

    r = client.patch(
        f"/api/v1/inventory/{inv_id}/adjust",
        headers=admin,
        json={"delta": -10},
    )
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "inventory_error"
    assert "below 0" in body["detail"].lower()
