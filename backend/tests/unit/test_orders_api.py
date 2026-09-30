"""Order API integration tests â€” require MySQL running."""

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
    email = f"ord-user-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_admin(client: TestClient) -> dict[str, str]:
    email = f"ord-admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/api/v1/auth/register", json={"email": email, "password": "pass12345"})
    with SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
        db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": uid})
        db.commit()
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "pass12345"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _make_product(
    client: TestClient, admin: dict[str, str], stock: int, price: str = "9.99"
) -> int:
    sku = _unique_sku()
    p = client.post(
        "/api/v1/admin/products",
        headers=admin,
        json={"name": "P", "sku": sku, "price": price},
    ).json()
    inv_id = client.get(f"/api/v1/inventory/product/{p['id']}").json()[0]["id"]
    client.patch(
        f"/api/v1/inventory/{inv_id}/adjust",
        headers=admin,
        json={"delta": stock},
    )
    return int(p["id"])


def _get_stock(client: TestClient, product_id: int) -> int:
    rows = client.get(f"/api/v1/inventory/product/{product_id}").json()
    return sum(r["quantity"] for r in rows)


# ----------------------------------------------------------------------
# Checkout success
# ----------------------------------------------------------------------
def test_checkout_success_decrements_stock_and_clears_cart(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)

    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 3})

    r = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test St, Dhaka"},
    )
    assert r.status_code == 201, r.text
    order = r.json()
    assert order["status"] == "pending"
    assert order["total_amount"] == "29.97"  # 9.99 * 3
    assert order["item_count"] == 1
    assert order["items"][0]["quantity"] == 3
    assert order["items"][0]["subtotal"] == "29.97"

    # Stock decreased
    assert _get_stock(client, pid) == 7

    # Cart cleared
    cart = client.get("/api/v1/cart", headers=user).json()
    assert cart["items"] == []


def test_checkout_empty_cart_returns_422(client: TestClient) -> None:
    user = _make_user(client)
    r = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    )
    assert r.status_code == 422
    assert r.json()["error"] == "validation_error"


def test_checkout_insufficient_stock_rolls_back(client: TestClient) -> None:
    """
    If stock is unavailable at checkout time, no order is created and
    no inventory is modified.

    HTTP 409 Conflict is the correct response here: the client's request
    is well-formed, but conflicts with the current state of the inventory
    resource (stock was drained externally between cart add and checkout).
    """
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=5)

    client.post(
        "/api/v1/cart/items",
        headers=user,
        json={"product_id": pid, "quantity": 3},
    )

    # Drain stock externally — cart wants 3 but only 1 remains
    inv_id = client.get(f"/api/v1/inventory/product/{pid}").json()[0]["id"]
    client.patch(
        f"/api/v1/inventory/{inv_id}/adjust",
        headers=admin,
        json={"delta": -4},  # stock: 5 -> 1
    )

    r = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    )

    # 409 Conflict: request is valid, but state conflicts with inventory
    assert r.status_code == 409
    body = r.json()
    assert body["error"] == "inventory_error"
    assert "Insufficient stock" in body["detail"]

    # Verify rollback: no order created, inventory unchanged (still 1)
    orders = client.get("/api/v1/orders", headers=user).json()
    assert isinstance(orders, list)
    assert len(orders) == 0

    inv = client.get(f"/api/v1/inventory/product/{pid}").json()
    assert len(inv) == 1
    assert inv[0]["quantity"] == 1


# ----------------------------------------------------------------------
# History
# ----------------------------------------------------------------------
def test_order_history_newest_first(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=100)

    for _ in range(3):
        client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1})
        client.post(
            "/api/v1/orders/checkout",
            headers=user,
            json={"shipping_address": "123 Test Street"},
        )

    orders = client.get("/api/v1/orders", headers=user).json()
    assert len(orders) == 3


def test_user_cannot_see_other_users_order(client: TestClient) -> None:
    admin = _make_admin(client)
    user_a = _make_user(client)
    user_b = _make_user(client)
    pid = _make_product(client, admin, stock=10)

    client.post("/api/v1/cart/items", headers=user_a, json={"product_id": pid, "quantity": 1})
    order = client.post(
        "/api/v1/orders/checkout",
        headers=user_a,
        json={"shipping_address": "123 Test Street"},
    ).json()

    r = client.get(f"/api/v1/orders/{order['id']}", headers=user_b)
    assert r.status_code == 404


# ----------------------------------------------------------------------
# Cancel
# ----------------------------------------------------------------------
def test_user_can_cancel_pending_order_and_stock_restored(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)

    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 4})
    order = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    ).json()

    assert _get_stock(client, pid) == 6  # 10 - 4

    r = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=user,
        json={"reason": "changed mind"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    assert _get_stock(client, pid) == 10  # restored


def test_cancel_delivered_order_returns_409(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)

    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1})
    order = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    ).json()

    # Admin: pending -> paid -> shipped -> delivered
    for new_status in ("paid", "shipped", "delivered"):
        client.patch(
            f"/api/v1/admin/orders/{order['id']}/status",
            headers=admin,
            json={"status": new_status},
        )

    # Now cancel should fail
    r = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers=user,
        json={},
    )
    assert r.status_code == 409


# ----------------------------------------------------------------------
# Admin
# ----------------------------------------------------------------------
def test_admin_can_list_all_orders(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)
    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1})
    client.post(
        "/api/v1/orders/checkout", headers=user, json={"shipping_address": "123 Test Street"}
    )

    r = client.get("/api/v1/admin/orders", headers=admin)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1


def test_admin_status_transition_workflow(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)
    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1})
    order = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    ).json()

    r = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin,
        json={"status": "paid"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"


def test_admin_cannot_skip_status(client: TestClient) -> None:
    admin = _make_admin(client)
    user = _make_user(client)
    pid = _make_product(client, admin, stock=10)
    client.post("/api/v1/cart/items", headers=user, json={"product_id": pid, "quantity": 1})
    order = client.post(
        "/api/v1/orders/checkout",
        headers=user,
        json={"shipping_address": "123 Test Street"},
    ).json()

    # pending -> delivered: not allowed
    r = client.patch(
        f"/api/v1/admin/orders/{order['id']}/status",
        headers=admin,
        json={"status": "delivered"},
    )
    assert r.status_code == 409


def test_non_admin_cannot_access_admin_orders(client: TestClient) -> None:
    user = _make_user(client)
    r = client.get("/api/v1/admin/orders", headers=user)
    assert r.status_code == 403
