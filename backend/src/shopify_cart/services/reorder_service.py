"""
Reorder suggestion service.

Uses a simple moving average of recent daily sales to estimate
demand, then suggests a reorder quantity that covers lead time +
safety stock.

Formula:
    avg_daily_demand = mean(last N days of sales for this product)
    lead_time_days   = configured per product-location (default 7)
    safety_stock     = avg_daily_demand * safety_multiplier (default 1.5)
    target_stock     = avg_daily_demand * lead_time_days + safety_stock
    reorder_qty      = max(0, ceil(target_stock - current_qty))
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopify_cart.logging_config import get_logger
from shopify_cart.models.analytics import DailySales
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product

logger = get_logger(__name__)


# Defaults — can be made per-product in future milestones
DEFAULT_LEAD_TIME_DAYS = 7
DEFAULT_SAFETY_MULTIPLIER = 1.5
DEFAULT_LOOKBACK_DAYS = 30
MIN_REORDER_QTY = 5


@dataclass(frozen=True)
class ReorderSuggestion:
    product_id: int
    sku: str
    name: str
    location: str
    current_quantity: int
    low_stock_threshold: int
    avg_daily_demand: float
    lookback_days: int
    lead_time_days: int
    safety_multiplier: float
    target_stock: int
    suggested_reorder_qty: int
    reason: str


class ReorderService:
    """Compute reorder suggestions from recent sales history."""

    @staticmethod
    def _avg_daily_demand(
        db: Session,
        product_id: int,
        lookback_days: int,
    ) -> float:
        """Mean daily quantity sold over the lookback window (0 if no data)."""
        since = date.today() - timedelta(days=lookback_days)
        total_qty = db.execute(
            select(func.coalesce(func.sum(DailySales.quantity), 0)).where(
                DailySales.product_id == product_id,
                DailySales.sales_date >= since,
            )
        ).scalar_one()

        avg = float(total_qty) / max(lookback_days, 1)
        return avg

    @staticmethod
    def suggest_for_inventory(
        db: Session,
        inv: Inventory,
        *,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        lead_time_days: int = DEFAULT_LEAD_TIME_DAYS,
        safety_multiplier: float = DEFAULT_SAFETY_MULTIPLIER,
    ) -> ReorderSuggestion:
        """Compute reorder suggestion for one inventory row."""
        product = db.get(Product, inv.product_id)
        if product is None:
            raise ValueError(f"Product {inv.product_id} not found.")

        avg_daily = ReorderService._avg_daily_demand(db, inv.product_id, lookback_days)

        # Safety stock = avg daily * multiplier (buffer for demand spikes)
        safety_stock = avg_daily * safety_multiplier

        # Target = demand during lead time + safety stock
        target_stock = avg_daily * lead_time_days + safety_stock

        gap = target_stock - inv.quantity
        suggested_qty = max(0, math.ceil(gap)) if gap > 0 else 0

        # Enforce a minimum reorder whenever low-stock is triggered
        if inv.is_low_stock and suggested_qty < MIN_REORDER_QTY:
            suggested_qty = MIN_REORDER_QTY

        # Reason string for the admin UI
        if avg_daily == 0:
            reason = "no recent sales — using minimum reorder"
        elif suggested_qty == 0:
            reason = "stock above target — no reorder needed"
        elif inv.is_low_stock:
            reason = (
                f"low stock ({inv.quantity} <= {inv.low_stock_threshold}); "
                f"avg {avg_daily:.2f}/day over {lookback_days}d"
            )
        else:
            reason = (
                f"below target ({inv.quantity} < {target_stock:.0f}); "
                f"avg {avg_daily:.2f}/day over {lookback_days}d"
            )

        return ReorderSuggestion(
            product_id=inv.product_id,
            sku=product.sku,
            name=product.name,
            location=inv.location,
            current_quantity=inv.quantity,
            low_stock_threshold=inv.low_stock_threshold,
            avg_daily_demand=round(avg_daily, 4),
            lookback_days=lookback_days,
            lead_time_days=lead_time_days,
            safety_multiplier=safety_multiplier,
            target_stock=math.ceil(target_stock),
            suggested_reorder_qty=suggested_qty,
            reason=reason,
        )

    @staticmethod
    def suggest_all(
        db: Session,
        *,
        low_stock_only: bool = True,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
        limit: int = 100,
    ) -> list[ReorderSuggestion]:
        """
        Compute suggestions for inventory rows.

        By default only low-stock rows are considered — this keeps the
        output actionable for the admin.
        """
        stmt = select(Inventory)
        if low_stock_only:
            # SQL-side filter: quantity <= low_stock_threshold
            stmt = stmt.where(Inventory.quantity <= Inventory.low_stock_threshold)
        stmt = stmt.order_by(Inventory.quantity.asc()).limit(limit)

        rows = list(db.execute(stmt).scalars().all())
        suggestions: list[ReorderSuggestion] = []
        for inv in rows:
            try:
                s = ReorderService.suggest_for_inventory(db, inv, lookback_days=lookback_days)
                suggestions.append(s)
            except ValueError:
                logger.warning(
                    "reorder_skip_missing_product",
                    product_id=inv.product_id,
                    inventory_id=inv.id,
                )
        return suggestions
