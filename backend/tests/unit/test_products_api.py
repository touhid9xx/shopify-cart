"""Product API integration tests — require MySQL running."""

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


def _make_admin_token(client: TestClient, db) -> str:
    email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "admin12345"},
    )
    # Promote to admin directly
    user = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
    db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": user})
    db.commit()

    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "admin12345"},
    ).json()
    return tokens["access_token"]


@pytest.fixture
def admin_headers(client: TestClient) -> dict[str, str]:
    with SessionLocal() as db:
        token = _make_admin_token(client, db)
    return {"Authorization": f"Bearer {token}"}


def _unique_sku() -> str:
    return f"SKU-{uuid.uuid4().hex[:8].upper()}"


def test_create_product_requires_admin(client: TestClient) -> None:
    r = client.post(
        "/api/v1/admin/products",
        json={"name": "X", "sku": _unique_sku(), "price": "9.99"},
    )
    assert r.status_code == 401  # no token


def test_admin_can_create_product(client: TestClient, admin_headers: dict[str, str]) -> None:
    sku = _unique_sku()
    r = client.post(
        "/api/v1/admin/products",
        headers=admin_headers,
        json={"name": "Blue Shirt", "sku": sku, "price": "19.99"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sku"] == sku
    assert body["price"] == "19.99"
    assert body["is_active"] is True


def test_duplicate_sku_returns_409(client: TestClient, admin_headers: dict[str, str]) -> None:
    sku = _unique_sku()
    payload = {"name": "X", "sku": sku, "price": "5.00"}
    r1 = client.post("/api/v1/admin/products", headers=admin_headers, json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/admin/products", headers=admin_headers, json=payload)
    assert r2.status_code == 409


def test_public_can_list_products(client: TestClient, admin_headers: dict[str, str]) -> None:
    # create one first
    client.post(
        "/api/v1/admin/products",
        headers=admin_headers,
        json={"name": "P", "sku": _unique_sku(), "price": "1.00"},
    )
    r = client.get("/api/v1/products")
    assert r.status_code == 200
    body = r.json()
    assert "items" in body
    assert "total" in body
    assert "page" in body


def test_admin_can_update_product(client: TestClient, admin_headers: dict[str, str]) -> None:
    sku = _unique_sku()
    created = client.post(
        "/api/v1/admin/products",
        headers=admin_headers,
        json={"name": "Old", "sku": sku, "price": "10.00"},
    ).json()
    r = client.put(
        f"/api/v1/admin/products/{created['id']}",
        headers=admin_headers,
        json={"name": "New", "price": "12.50"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "New"
    assert r.json()["price"] == "12.50"


def test_admin_can_soft_delete(client: TestClient, admin_headers: dict[str, str]) -> None:
    sku = _unique_sku()
    created = client.post(
        "/api/v1/admin/products",
        headers=admin_headers,
        json={"name": "Bye", "sku": sku, "price": "1.00"},
    ).json()
    r = client.delete(
        f"/api/v1/admin/products/{created['id']}",
        headers=admin_headers,
    )
    assert r.status_code == 204

    # Public detail should still 200 (soft delete), but is_active=false
    r = client.get(f"/api/v1/products/{created['id']}")
    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_categories_endpoints(client: TestClient) -> None:
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    assert "items" in r.json()

    r = client.get("/api/v1/categories/tree")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
