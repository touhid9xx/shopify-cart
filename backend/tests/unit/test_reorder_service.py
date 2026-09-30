"""Unit tests for reorder service."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date, timedelta
from typing import cast

import pytest
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shopify_cart.db.base import Base
from shopify_cart.models.analytics import DailySales
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product
from shopify_cart.services.reorder_service import (
    DEFAULT_LEAD_TIME_DAYS,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_SAFETY_MULTIPLIER,
    MIN_REORDER_QTY,
    ReorderService,
)


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
# Demand calculation
# ----------------------------------------------------------------------
def test_avg_daily_demand_no_sales(in_memory_db: Session) -> None:
    product, _ = _make_product_with_inventory(in_memory_db, qty=100)
    avg = ReorderService._avg_daily_demand(in_memory_db, product.id, lookback_days=30)
    assert avg == 0.0


def test_avg_daily_demand_with_sales(in_memory_db: Session) -> None:
    product, _ = _make_product_with_inventory(in_memory_db, qty=100)
    _add_sales_history(in_memory_db, product.id, days=10, qty_per_day=3)
    avg = ReorderService._avg_daily_demand(in_memory_db, product.id, lookback_days=30)
    # 10 days * 3 units = 30 units over 30 days = 1.0/day
    assert avg == pytest.approx(30 / 30, abs=0.01)


# ----------------------------------------------------------------------
# Suggestion logic
# ----------------------------------------------------------------------
def test_suggestion_when_stock_is_high(in_memory_db: Session) -> None:
    """High stock, no sales — no reorder needed."""
    product, inv = _make_product_with_inventory(in_memory_db, qty=1000, threshold=5)
    _ = product
    s = ReorderService.suggest_for_inventory(in_memory_db, inv)
    assert s.suggested_reorder_qty == 0
    assert "no recent sales" in s.reason or "above target" in s.reason


def test_suggestion_when_low_stock_with_sales(in_memory_db: Session) -> None:
    """Low stock + steady sales → meaningful reorder qty."""
    product, inv = _make_product_with_inventory(in_memory_db, qty=3, threshold=10)
    _add_sales_history(in_memory_db, product.id, days=10, qty_per_day=5)

    s = ReorderService.suggest_for_inventory(in_memory_db, inv)
    # avg = 5/day over 30 days lookback → 50/30 = 1.667
    # target = 1.667 * 7 + 1.667 * 1.5 = 14.17
    # gap = 14.17 - 3 = 11.17 → ceil = 12
    assert s.suggested_reorder_qty > 0
    assert s.current_quantity == 3
    assert s.low_stock_threshold == 10
    assert "low stock" in s.reason


def test_suggestion_when_low_stock_no_sales(in_memory_db: Session) -> None:
    """Low stock but no sales data → fall back to MIN_REORDER_QTY."""
    product, inv = _make_product_with_inventory(in_memory_db, qty=1, threshold=5)
    _ = product
    s = ReorderService.suggest_for_inventory(in_memory_db, inv)
    assert s.suggested_reorder_qty == MIN_REORDER_QTY
    assert "no recent sales" in s.reason


def test_suggest_all_low_stock_only(in_memory_db: Session) -> None:
    """Only low-stock products appear in suggestions."""
    # Low-stock product with steady sales
    p1, _ = _make_product_with_inventory(in_memory_db, qty=2, threshold=5)
    _add_sales_history(in_memory_db, p1.id, days=10, qty_per_day=4)

    # High-stock product (should NOT appear)
    p2, _ = _make_product_with_inventory(in_memory_db, qty=100, threshold=5)
    _ = p2

    suggestions = ReorderService.suggest_all(in_memory_db, low_stock_only=True, lookback_days=30)
    # Only p1 should appear (p2 is above threshold)
    assert len(suggestions) == 1
    assert suggestions[0].product_id == p1.id


def test_lead_time_and_safety_defaults_in_suggestion(in_memory_db: Session) -> None:
    product, inv = _make_product_with_inventory(in_memory_db, qty=0, threshold=5)
    _add_sales_history(in_memory_db, product.id, days=5, qty_per_day=2)
    s = ReorderService.suggest_for_inventory(in_memory_db, inv)
    assert s.lead_time_days == DEFAULT_LEAD_TIME_DAYS
    assert s.safety_multiplier == DEFAULT_SAFETY_MULTIPLIER
    assert s.lookback_days == DEFAULT_LOOKBACK_DAYS
