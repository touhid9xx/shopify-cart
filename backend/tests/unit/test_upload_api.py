"""Integration tests for /admin/products/upload (auto-categorization).

Requires:
  - MySQL
  - MLflow with registered model
  - Kafka (graceful if offline)
"""

from __future__ import annotations

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shopify_cart.db.session import SessionLocal
from shopify_cart.ml.predict import get_predictor


@pytest.fixture(autouse=True)
def _require_mysql() -> None:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar()
    except SQLAlchemyError as exc:
        pytest.skip(f"MySQL not available: {exc}")


@pytest.fixture(autouse=True)
def _require_model() -> None:
    p = get_predictor()
    try:
        if not p.is_loaded:
            p.load()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"ML model not available: {exc}")
    if not p.is_loaded:
        pytest.skip("ML predictor not loaded")


def _unique_sku() -> str:
    return f"UPL-{uuid.uuid4().hex[:8].upper()}"


def _png(color: tuple[int, int, int] = (200, 100, 50)) -> bytes:
    img = Image.new("RGB", (100, 100), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_admin(client: TestClient) -> dict[str, str]:
    email = f"upload-admin-{uuid.uuid4().hex[:8]}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "pass12345"},
    )
    with SessionLocal() as db:
        uid = db.execute(text("SELECT id FROM users WHERE email=:e"), {"e": email}).scalar_one()
        db.execute(text("UPDATE users SET is_admin=1 WHERE id=:i"), {"i": uid})
        db.commit()
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "pass12345"},
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_upload_requires_admin(client: TestClient) -> None:
    files = {"image": ("t.png", _png(), "image/png")}
    data = {"name": "P", "price": "9.99"}
    r = client.post("/api/v1/admin/products/upload", files=files, data=data)
    assert r.status_code == 401


def test_upload_returns_created_or_review(
    client: TestClient,
) -> None:
    admin = _make_admin(client)
    sku = _unique_sku()
    files = {"image": ("t.png", _png(), "image/png")}
    data = {
        "name": "Upload Test Product",
        "price": "24.99",
        "sku": sku,
        "initial_quantity": "5",
    }
    r = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files,
        data=data,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] in {"created", "needs_review"}

    if body["status"] == "created":
        # Product must be persisted with the given SKU
        from sqlalchemy import select

        from shopify_cart.models.product import Product

        with SessionLocal() as db:
            p = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
            assert p is not None
            assert p.name == "Upload Test Product"
        assert body["product_id"] > 0
        assert body["category_slug"]
    else:
        # needs_review can happen for two reasons:
        #   (a) confidence < threshold
        #   (b) confidence >= threshold but no matching category exists
        # In both cases we must return suggestions for the admin.
        assert isinstance(body["suggestions"], list)
        assert len(body["suggestions"]) >= 1
        # If confidence was high, the reason must be a category mismatch
        if body["confidence"] >= body["threshold"]:
            assert "no matching category" in body["message"].lower()


def test_upload_force_category_slug(client: TestClient) -> None:
    admin = _make_admin(client)
    sku = _unique_sku()
    # Assume seed created "accessories" — if not, this test skips
    with SessionLocal() as db:
        has_accessories = db.execute(
            text("SELECT 1 FROM categories WHERE slug='accessories' LIMIT 1")
        ).first()
    if has_accessories is None:
        pytest.skip("Category 'accessories' not seeded")

    files = {"image": ("t.png", _png((50, 100, 200)), "image/png")}
    data = {
        "name": "Forced Category Product",
        "price": "12.50",
        "sku": sku,
        "force_category_slug": "accessories",
    }
    r = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files,
        data=data,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "created"
    assert body["category_slug"] == "accessories"


def test_upload_rejects_wrong_content_type(client: TestClient) -> None:
    admin = _make_admin(client)
    files = {"image": ("t.txt", b"hello", "text/plain")}
    data = {"name": "P", "price": "9.99"}
    r = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files,
        data=data,
    )
    assert r.status_code == 422


def test_upload_rejects_invalid_price(client: TestClient) -> None:
    admin = _make_admin(client)
    files = {"image": ("t.png", _png(), "image/png")}
    data = {"name": "P", "price": "not-a-number"}
    r = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files,
        data=data,
    )
    assert r.status_code == 422


def test_upload_rejects_duplicate_sku(client: TestClient) -> None:
    admin = _make_admin(client)
    sku = _unique_sku()
    files = {"image": ("t.png", _png(), "image/png")}
    data = {
        "name": "P",
        "price": "9.99",
        "sku": sku,
        "force_category_slug": "accessories",
    }
    r1 = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files,
        data=data,
    )
    if r1.status_code != 200 or r1.json().get("status") != "created":
        pytest.skip("First upload did not create a product")

    # Second upload with same SKU
    files2 = {"image": ("t.png", _png((10, 20, 30)), "image/png")}
    r2 = client.post(
        "/api/v1/admin/products/upload",
        headers=admin,
        files=files2,
        data=data,
    )
    assert r2.status_code == 409
