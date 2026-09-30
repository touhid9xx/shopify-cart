"""Integration tests for /admin/inventory/alerts + /admin/inventory/reorder-suggestions.

Uses an in-memory SQLite database for isolation — no MySQL required.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import cast

import pytest
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shopify_cart.db.base import Base
from shopify_cart.models.analytics import DailySales, InventoryAlert
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def in_memory_db() -> Iterator[Session]:
    """SQLite in-memory DB with the tables we need."""
    engine = create_engine("sqlite:///:memory:")
    tables = [
        cast(Table, Category.__table__),
        cast(Table, Product.__table__),
        cast(Table, Inventory.__table__),
        cast(Table, DailySales.__table__),
        cast(Table, InventoryAlert.__table__),
    ]
    Base.metadata.create_all(engine, tables=tables)

    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _make_product_with_inventory(
    db: Session,
    *,
    qty: int,
    threshold: int = 5,
    sku: str | None = None,
) -> tuple[Product, Inventory]:
    """Create a product + inventory with unique SKU by default."""
    product = Product(
        name="Test Product",
        sku=sku or f"TEST-{uuid.uuid4().hex[:8].upper()}",
        price=9.99,
        is_active=True,
    )
    db.add(product)
    db.flush()

    inv = Inventory(
        product_id=product.id,
        location="default",
        quantity=qty,
        low_stock_threshold=threshold,
    )
    db.add(inv)
    db.commit()
    db.refresh(product)
    db.refresh(inv)
    return product, inv


def _make_alert(
    db: Session,
    *,
    product_id: int,
    quantity: int = 2,
    threshold: int = 5,
) -> InventoryAlert:
    alert = InventoryAlert(
        product_id=product_id,
        location="default",
        quantity=quantity,
        threshold=threshold,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def _add_sales_history(
    db: Session,
    product_id: int,
    *,
    days: int,
    qty_per_day: int,
) -> None:
    """Insert DailySales rows for the last `days` days."""
    today = date.today()
    for i in range(days):
        db.add(
            DailySales(
                sales_date=today - timedelta(days=i),
                product_id=product_id,
                quantity=qty_per_day,
                revenue=9.99 * qty_per_day,
                order_count=1,
            )
        )
    db.commit()


# ----------------------------------------------------------------------
# Tests — reorder suggestion integration
# ----------------------------------------------------------------------
def test_suggest_all_low_stock_only(in_memory_db: Session) -> None:
    """Only low-stock products appear in suggestions."""
    # Low-stock product with steady sales
    p1, _ = _make_product_with_inventory(in_memory_db, qty=2, threshold=5)
    _add_sales_history(in_memory_db, p1.id, days=10, qty_per_day=4)

    # High-stock product (should NOT appear)
    p2, _ = _make_product_with_inventory(in_memory_db, qty=100, threshold=5)
    _ = p2  # silence unused warning

    from shopify_cart.services.reorder_service import ReorderService

    suggestions = ReorderService.suggest_all(in_memory_db, low_stock_only=True, lookback_days=30)
    assert len(suggestions) == 1
    assert suggestions[0].product_id == p1.id
