"""Inventory business logic — read + adjust + Kafka events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from shopify_cart.exceptions import InventoryError, NotFoundError
from shopify_cart.kafka.events import InventoryChangedEvent, InventoryLowEvent
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.models.inventory import Inventory

logger = get_logger(__name__)


class InventoryService:
    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    @staticmethod
    def list_for_product(db: Session, product_id: int) -> list[Inventory]:
        return list(
            db.execute(
                select(Inventory)
                .where(Inventory.product_id == product_id)
                .order_by(Inventory.location)
            )
            .scalars()
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, inventory_id: int) -> Inventory:
        inv = db.get(Inventory, inventory_id)
        if inv is None:
            raise NotFoundError(f"Inventory {inventory_id} not found.")
        return inv

    @staticmethod
    def get_for_product_location(db: Session, product_id: int, location: str) -> Inventory | None:
        return db.execute(
            select(Inventory).where(
                Inventory.product_id == product_id,
                Inventory.location == location,
            )
        ).scalar_one_or_none()

    # ------------------------------------------------------------------
    # Adjust (increment / decrement)
    # ------------------------------------------------------------------
    @staticmethod
    async def adjust(
        db: Session,
        producer: KafkaProducer,
        inventory_id: int,
        *,
        delta: int,
        reason: str | None = None,
    ) -> Inventory:
        inv = InventoryService.get_by_id(db, inventory_id)
        old_qty = inv.quantity
        new_qty = old_qty + delta

        if new_qty < 0:
            raise InventoryError(f"Cannot reduce stock below 0 (current={old_qty}, delta={delta}).")

        inv.quantity = new_qty
        db.commit()
        db.refresh(inv)

        # ---- Emit change event (always) ----
        changed_event = InventoryChangedEvent(
            product_id=inv.product_id,
            location=inv.location,
            old_quantity=old_qty,
            new_quantity=new_qty,
        )
        await producer.publish("inventory.changed", changed_event, key=str(inv.product_id))

        # ---- Emit low-stock event on threshold crossing ----
        # Emit only when stock transitions from "at or above threshold"
        # to "strictly below threshold". This covers:
        #   (a) old > threshold → new <= threshold  (fell below)
        #   (b) old == threshold → new < threshold  (first time below)
        # and avoids re-emitting on every subsequent decrement while
        # already below threshold (the consumer de-duplicates anyway,
        # but we save Kafka traffic).
        threshold = inv.low_stock_threshold
        crossed_down = old_qty >= threshold and new_qty < threshold

        if crossed_down:
            low_event = InventoryLowEvent(
                product_id=inv.product_id,
                location=inv.location,
                quantity=new_qty,
                threshold=threshold,
            )
            await producer.publish("inventory.low", low_event, key=str(inv.product_id))
            logger.warning(
                "inventory_low_alert_triggered",
                product_id=inv.product_id,
                location=inv.location,
                old_quantity=old_qty,
                new_quantity=new_qty,
                threshold=threshold,
            )

        logger.info(
            "inventory_adjusted",
            inventory_id=inv.id,
            product_id=inv.product_id,
            old=old_qty,
            new=new_qty,
            reason=reason,
        )
        return inv
