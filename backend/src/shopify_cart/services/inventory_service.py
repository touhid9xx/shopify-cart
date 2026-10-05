"""Inventory business logic — read + adjust + Kafka events."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, func, or_, select
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
    def get_for_product_location(
        db: Session,
        product_id: int,
        location: str,
    ) -> Inventory | None:
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
        await producer.publish(
            "inventory.changed",
            changed_event,
            key=str(inv.product_id),
        )

        # ---- Emit low-stock event on threshold crossing ----
        # Only when stock transitions from "at or above threshold" to
        # "strictly below threshold". Avoids re-emitting on every
        # subsequent decrement while already below threshold.
        threshold = inv.low_stock_threshold
        crossed_down = old_qty >= threshold and new_qty < threshold

        if crossed_down:
            low_event = InventoryLowEvent(
                product_id=inv.product_id,
                location=inv.location,
                quantity=new_qty,
                threshold=threshold,
            )
            await producer.publish(
                "inventory.low",
                low_event,
                key=str(inv.product_id),
            )
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

    # ------------------------------------------------------------------
    # Admin: list all inventory (paginated, filterable)
    # ------------------------------------------------------------------
    @staticmethod
    def list_all(
        db: Session,
        *,
        low_stock_only: bool = False,
        out_of_stock_only: bool = False,
        search: str | None = None,
        location: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Inventory], int]:
        """
        Return (rows, total) for the admin inventory table.

        - ``search``: matches product.sku OR product.name (ILIKE)
        - ``location``: exact match on Inventory.location
        - ``low_stock_only``: quantity <= low_stock_threshold
        - ``out_of_stock_only``: quantity == 0
        """
        from shopify_cart.models.product import Product

        stmt = select(Inventory).join(Product, Product.id == Inventory.product_id)
        count_stmt = select(func.count(Inventory.id)).join(
            Product, Product.id == Inventory.product_id
        )

        if low_stock_only:
            cond = Inventory.quantity <= Inventory.low_stock_threshold
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if out_of_stock_only:
            cond = Inventory.quantity == 0
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if location is not None:
            cond = Inventory.location == location
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        if search:
            term = f"%{search.strip()}%"
            cond = or_(Product.sku.ilike(term), Product.name.ilike(term))
            stmt = stmt.where(cond)
            count_stmt = count_stmt.where(cond)

        stmt = stmt.order_by(Inventory.quantity.asc(), Inventory.id.asc())

        total = db.execute(count_stmt).scalar_one()
        rows = list(db.execute(stmt.offset(offset).limit(limit)).scalars().all())
        return rows, total

    # ------------------------------------------------------------------
    # Admin: stats / KPIs
    # ------------------------------------------------------------------
    @staticmethod
    def stats(db: Session) -> dict[str, int | Decimal]:
        """
        Return aggregated inventory KPIs.

        Uses two queries — one for counts, one for value — because value
        requires a join with Product.price.
        """
        from shopify_cart.models.product import Product

        # Counts + threshold comparisons (no join needed)
        row = db.execute(
            select(
                func.count(Inventory.id).label("total"),
                func.coalesce(func.sum(Inventory.quantity), 0).label("units"),
                func.coalesce(
                    func.sum(
                        case(  # ✅ FIXED
                            (
                                Inventory.quantity <= Inventory.low_stock_threshold,
                                1,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ).label("low_stock"),
                func.coalesce(
                    func.sum(
                        case((Inventory.quantity == 0, 1), else_=0)  # ✅ FIXED
                    ),
                    0,
                ).label("out_of_stock"),
            )
        ).one()

        # Distinct products
        total_skus = db.execute(
            select(func.count(func.distinct(Inventory.product_id)))
        ).scalar_one()

        # Total value = sum(quantity * price) via join
        total_value = db.execute(
            select(
                func.coalesce(
                    func.sum(Inventory.quantity * Product.price),
                    Decimal("0"),
                )
            ).join(Product, Product.id == Inventory.product_id)
        ).scalar_one()

        return {
            "total_skus": int(total_skus or 0),
            "total_units": int(row.units or 0),
            "low_stock_count": int(row.low_stock or 0),
            "out_of_stock_count": int(row.out_of_stock or 0),
            "total_inventory_value": Decimal(total_value or 0),
        }

    # ------------------------------------------------------------------
    # Admin: adjust by product_id + location (upsert)
    # ------------------------------------------------------------------
    @staticmethod
    async def adjust_by_product_location(
        db: Session,
        producer: KafkaProducer,
        *,
        product_id: int,
        location: str,
        delta: int,
        reason: str | None = None,
    ) -> Inventory:
        """
        Adjust stock for (product_id, location).

        If no row exists, create one with quantity = delta.
        Negative resulting quantity -> InventoryError.
        Emits ``inventory.changed`` and (if crossed) ``inventory.low``.
        """
        from shopify_cart.models.product import Product

        product = db.get(Product, product_id)
        if product is None:
            raise NotFoundError(f"Product {product_id} not found.")

        inv = InventoryService.get_for_product_location(db, product_id, location)
        if inv is None:
            # Create new row
            if delta < 0:
                raise InventoryError(
                    f"Cannot reduce stock for non-existent inventory "
                    f"(product={product_id}, location={location!r})."
                )
            inv = Inventory(
                product_id=product_id,
                location=location,
                quantity=delta,
                low_stock_threshold=5,
            )
            db.add(inv)
            db.commit()
            db.refresh(inv)

            # Emit creation as a change
            await producer.publish(
                "inventory.changed",
                InventoryChangedEvent(
                    product_id=inv.product_id,
                    location=inv.location,
                    old_quantity=0,
                    new_quantity=inv.quantity,
                ),
                key=str(inv.product_id),
            )
            logger.info(
                "inventory_created",
                inventory_id=inv.id,
                product_id=inv.product_id,
                location=inv.location,
                quantity=inv.quantity,
                reason=reason,
            )
            return inv

        # Existing row -> delegate to the standard adjust
        return await InventoryService.adjust(db, producer, inv.id, delta=delta, reason=reason)
