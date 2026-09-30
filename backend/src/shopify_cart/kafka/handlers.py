"""Kafka event handlers — write side-effects to DB.

Each handler receives `(topic, payload_dict)`. Handler must be
idempotent where possible — Kafka gives at-least-once delivery.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from shopify_cart.db.session import SessionLocal
from shopify_cart.kafka.events import Topics
from shopify_cart.logging_config import get_logger
from shopify_cart.models.analytics import DailySales, InventoryAlert
from shopify_cart.models.order import Order
from shopify_cart.models.order_item import OrderItem

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# product.created — log + (stub) search index update
# ----------------------------------------------------------------------
async def handle_product_created(topic: str, payload: dict[str, Any]) -> None:
    logger.info(
        "analytics_product_created",
        topic=topic,
        product_id=payload.get("product_id"),
        sku=payload.get("sku"),
        category_id=payload.get("category_id"),
    )
    # TODO(Milestone 13+): update search index


# ----------------------------------------------------------------------
# cart.updated — metric only
# ----------------------------------------------------------------------
async def handle_cart_updated(topic: str, payload: dict[str, Any]) -> None:
    logger.info(
        "metrics_cart_updated",
        topic=topic,
        cart_id=payload.get("cart_id"),
        item_count=payload.get("item_count"),
        total_amount=payload.get("total_amount"),
    )


# ----------------------------------------------------------------------
# order.placed — upsert DailySales rows
# ----------------------------------------------------------------------
async def handle_order_placed(topic: str, payload: dict[str, Any]) -> None:
    order_id = payload.get("order_id")
    if order_id is None:
        logger.warning("order_placed_missing_order_id", payload=payload)
        return

    db: Session = SessionLocal()
    try:
        order = db.get(Order, int(order_id))
        if order is None:
            logger.warning("order_placed_order_not_found", order_id=order_id)
            return

        items = db.execute(select(OrderItem).where(OrderItem.order_id == order.id)).scalars().all()

        today = date.today()
        for it in items:
            # if it.product_id is None:
            #     continue  # product hard-deleted; skip analytics

            # MySQL-specific upsert; use dialect-agnostic pattern for portability
            existing = db.execute(
                select(DailySales).where(
                    DailySales.sales_date == today,
                    DailySales.product_id == it.product_id,
                )
            ).scalar_one_or_none()

            if existing is None:
                row = DailySales(
                    sales_date=today,
                    product_id=it.product_id,
                    quantity=it.quantity,
                    revenue=it.subtotal,
                    order_count=1,
                )
                db.add(row)
            else:
                existing.quantity += it.quantity
                existing.revenue = (existing.revenue + it.subtotal).quantize(Decimal("0.01"))
                existing.order_count += 1

        db.commit()
        logger.info(
            "analytics_order_placed_recorded",
            order_id=order.id,
            item_count=len(items),
            sales_date=today.isoformat(),
        )
    except SQLAlchemyError:
        db.rollback()
        logger.exception("analytics_order_placed_failed", order_id=order_id)
    finally:
        db.close()


# ----------------------------------------------------------------------
# inventory.low — create alert row
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# inventory.low — create alert row
# ----------------------------------------------------------------------
async def handle_inventory_low(topic: str, payload: dict[str, Any]) -> None:
    product_id = payload.get("product_id")
    location = payload.get("location")
    quantity = payload.get("quantity")
    threshold = payload.get("threshold")

    if product_id is None or location is None:
        logger.warning("inventory_low_missing_fields", payload=payload)
        return

    db: Session = SessionLocal()
    try:
        # De-duplicate: if there is already an unresolved alert for this
        # (product, location) within the last hour, skip.
        # MySQL DATETIME is naive, so strip tzinfo before comparing.
        one_hour_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        existing = db.execute(
            select(InventoryAlert)
            .where(
                InventoryAlert.product_id == int(product_id),
                InventoryAlert.location == str(location),
                InventoryAlert.resolved_at.is_(None),
                InventoryAlert.created_at >= one_hour_ago,
            )
            .order_by(InventoryAlert.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()

        if existing is not None:
            logger.info(
                "inventory_low_already_open",
                product_id=product_id,
                location=location,
                existing_alert_id=existing.id,
            )
            return

        alert = InventoryAlert(
            product_id=int(product_id),
            location=str(location),
            quantity=int(quantity or 0),
            threshold=int(threshold or 0),
        )
        db.add(alert)
        db.commit()
        logger.warning(
            "inventory_low_alert_created",
            alert_id=alert.id,
            product_id=product_id,
            location=location,
            quantity=quantity,
            threshold=threshold,
        )
        # TODO(Milestone 15): send email via SMTP / SendGrid
    except SQLAlchemyError:
        db.rollback()
        logger.exception("inventory_low_handler_failed", product_id=product_id)
    finally:
        db.close()


# ----------------------------------------------------------------------
# order.cancelled — log (inventory restoration handled in order service)
# ----------------------------------------------------------------------
async def handle_order_cancelled(topic: str, payload: dict[str, Any]) -> None:
    logger.info(
        "analytics_order_cancelled",
        topic=topic,
        order_id=payload.get("order_id"),
        user_id=payload.get("user_id"),
        reason=payload.get("reason"),
    )


# ----------------------------------------------------------------------
# Registry
# ----------------------------------------------------------------------
def build_handlers() -> dict[str, Any]:
    """Return a mapping: topic -> handler coroutine."""
    return {
        Topics.PRODUCT_CREATED: handle_product_created,
        Topics.CART_UPDATED: handle_cart_updated,
        Topics.ORDER_PLACED: handle_order_placed,
        Topics.ORDER_CANCELLED: handle_order_cancelled,
        Topics.INVENTORY_LOW: handle_inventory_low,
    }
