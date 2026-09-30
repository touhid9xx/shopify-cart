"""Cart API integration tests — require MySQL running."""

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


def _make_user(client: TestClient) -> dict[str, str]:
    email = f"user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_admin(client: TestClient) -> dict[str, str]:
    email = f"cart-admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    with SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
        db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": uid})
        db.commit()
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_product_with_stock(client: TestClient, admin: dict[str, str], stock: int) -> int:
    sku = _unique_sku()
    p = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={"name": "P", "sku": sku, "price": "9.99"},
    ).json()
    inv_id = client.get(f"/api/v1/inventory/product/{p['id']}").json()[0]["id"]
    client.patch(
        f"/api/v1/inventory/{inv_id}/adjust",
        headers=admin,
        json={"delta": stock},
    )
    return int(p["id"])


def test_get_cart_creates_empty_cart(client: TestClient) -> None:
    user = _make_user(client)
    r = client.get("/api/v1/cart", headers=user)
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert body["item_count"] == 0
    assert body["total_amount"] == "0.00"


def test_cart_requires_auth(client: TestClient) -> None:
    assert client.get("/api/v1/cart").status_code == 401


def test_add_item_to_cart(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    r = client.post(
        "/api/v1/cart/items",
        headers=user,
        json={"product_id": pid, "quantity": 2},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["item_count"] == 1
    assert body["items"][0]["quantity"] == 2
    assert body["items"][0]["unit_price"] == "9.99"
    assert body["items"][0]["subtotal"] == "19.98"
    assert body["total_amount"] == "19.98"


def test_add_same_product_twice_increments_quantity(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 2})
    r = client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 3})
    body = r.json()
    assert body["item_count"] == 1
    assert body["items"][0]["quantity"] == 5


def test_add_more_than_stock_returns_409(client: TestClient) -> None:
    """Insufficient stock → 409 Conflict (state conflict, not malformed request)."""
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 2)

    r = client.post(
        "/api/v1/cart/items",
        headers=user,
        json={"product_id": pid, "quantity": 5},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "inventory_error"


def test_update_item_quantity(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    cart = client.post(
        "/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1}
    ).json()
    item_id = cart["items"][0]["id"]

    r = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=user,
        json={"quantity": 5},
    )
    assert r.status_code == 200
    assert r.json()["items"][0]["quantity"] == 5


def test_update_to_zero_removes_item(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    cart = client.post(
        "/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1}
    ).json()
    item_id = cart["items"][0]["id"]

    r = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=user,
        json={"quantity": 0},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_remove_item(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    cart = client.post(
        "/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 3}
    ).json()
    item_id = cart["items"][0]["id"]

    r = client.delete(f"/api/v1/cart/items/{item_id}", headers=user)
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_clear_cart(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid1 = _make_product_with_stock(client, admin, 10)
    pid2 = _make_product_with_stock(client, admin, 10)

    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid1, "quantity": 1})
    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid2, "quantity": 2})

    r = client.delete("/api/v1/cart", headers=user)
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total_amount"] == "0.00"


def test_user_cannot_touch_other_users_item(client: TestClient) -> None:
    admin = _make_admin(client)
    user_a = _make_user(client)
    user_b = _make_user(client)
    pid = _make_product_with_stock(client, admin, 10)

    cart_a = client.post(
        "/api/v1/cart/items", headers=user_a, json={"product_id": pid, "quantity": 1}
    ).json()
    item_id = cart_a["items"][0]["id"]

    # user_b tries to modify user_a's item
    r = client.patch(
        f"/api/v1/cart/items/{item_id}",
        headers=user_b,
        json={"quantity": 99},
    )
    assert r.status_code == 404
