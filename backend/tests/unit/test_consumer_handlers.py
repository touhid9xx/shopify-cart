"""Unit tests for Kafka handlers — DB-touching ones skipped if no MySQL."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from shopify_cart.db.session import SessionLocal
from shopify_cart.kafka.handlers import (
    build_handlers,
    handle_cart_updated,
    handle_inventory_low,
    handle_order_cancelled,
    handle_product_created,
)


def test_handler_registry_contains_core_topics() -> None:
    h = build_handlers()
    assert "product.created" in h
    assert "cart.updated" in h
    assert "order.placed" in h
    assert "order.cancelled" in h
    assert "inventory.low" in h


@pytest.mark.asyncio
async def test_handle_product_created_does_not_raise() -> None:
    await handle_product_created(
        "product.created",
        {"product_id": 1, "sku": "X", "category_id": 1},
    )


@pytest.mark.asyncio
async def test_handle_cart_updated_does_not_raise() -> None:
    await handle_cart_updated(
        "cart.updated",
        {"cart_id": 1, "item_count": 2, "total_amount": "19.98"},
    )


@pytest.mark.asyncio
async def test_handle_order_cancelled_does_not_raise() -> None:
    await handle_order_cancelled(
        "order.cancelled",
        {"order_id": 1, "user_id": 1, "reason": "test"},
    )


def _mysql_available() -> bool:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar()
        return True
    except SQLAlchemyError:
        return False


@pytest.mark.asyncio
async def test_inventory_low_creates_alert_row() -> None:
    if not _mysql_available():
        pytest.skip("MySQL not available")

    # Need a real product for FK
    from shopify_cart.models.product import Product

    with SessionLocal() as db:
        sku = f"ALERT-TEST-{uuid.uuid4().hex[:6]}"
        p = Product(name="Alert Product", sku=sku, price=1)
        db.add(p)
        db.commit()
        db.refresh(p)
        pid = p.id

    await handle_inventory_low(
        "inventory.low",
        {"product_id": pid, "location": "default", "quantity": 1, "threshold": 5},
    )

    with SessionLocal() as db:
        from shopify_cart.models.analytics import InventoryAlert

        alert = (
            db.query(InventoryAlert)
            .filter(
                InventoryAlert.product_id == pid,
                InventoryAlert.resolved_at.is_(None),
            )
            .first()
        )
        assert alert is not None
        assert alert.quantity == 1
        assert alert.threshold == 5

        # Second call should NOT create duplicate
        first_id = alert.id

    await handle_inventory_low(
        "inventory.low",
        {"product_id": pid, "location": "default", "quantity": 1, "threshold": 5},
    )

    with SessionLocal() as db:
        from shopify_cart.models.analytics import InventoryAlert

        count = (
            db.query(InventoryAlert)
            .filter(
                InventoryAlert.product_id == pid,
                InventoryAlert.resolved_at.is_(None),
            )
            .count()
        )
        assert count == 1
        _ = first_id  # silence linter
