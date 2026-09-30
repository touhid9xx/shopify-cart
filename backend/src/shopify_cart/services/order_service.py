"""Order business logic — atomic checkout, cancel, status transitions."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from shopify_cart.core.money import multiply_money, sum_money
from shopify_cart.exceptions import (
    ConflictError,
    InventoryError,
    NotFoundError,
    ValidationError,
)
from shopify_cart.kafka.events import (
    InventoryChangedEvent,
    OrderCancelledEvent,
    OrderPlacedEvent,
)
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.models.cart import Cart
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.order import Order, OrderStatus
from shopify_cart.models.order_item import OrderItem

logger = get_logger(__name__)


# Which status transitions are allowed.
_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


class OrderService:
    """All order lifecycle operations."""

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    @staticmethod
    def get_by_id(db: Session, order_id: int) -> Order:
        """Fetch an order by ID (with items eagerly loaded).

        Raises NotFoundError if missing.
        """
        order = db.execute(
            select(Order).where(Order.id == order_id).options(selectinload(Order.items))
        ).scalar_one_or_none()
        if order is None:
            raise NotFoundError(f"Order {order_id} not found.")
        return order

    @staticmethod
    def list_for_user(db: Session, user_id: int) -> list[Order]:
        """Return all orders for a user, newest first."""
        return list(
            db.execute(
                select(Order)
                .where(Order.user_id == user_id)
                .options(selectinload(Order.items))
                .order_by(Order.created_at.desc())
            )
            .scalars()
            .all()
        )

    # ------------------------------------------------------------------
    # Checkout — the atomic operation
    # ------------------------------------------------------------------
    @staticmethod
    async def checkout(
        db: Session,
        producer: KafkaProducer,
        *,
        user_id: int,
        shipping_address: str,
        notes: str | None = None,
    ) -> Order:
        """Cart → Order. All-or-nothing.

        Steps:
          1. Load cart (must be non-empty).
          2. Verify stock for every line (fail early if any short).
          3. Decrement inventory rows (row-level lock via SELECT ... FOR UPDATE).
          4. Create Order + OrderItems (snapshot product data).
          5. Delete all CartItems.
          6. Commit — if anything fails, rollback leaves the DB unchanged.
          7. Publish events (only after commit succeeds).
        """
        # -------- 1. Load cart with items --------
        cart = db.execute(
            select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items))
        ).scalar_one_or_none()

        if cart is None or not cart.items:
            raise ValidationError("Cart is empty — nothing to checkout.")

        # Freeze the item list for iteration
        cart_items = list(cart.items)

        # -------- 2. Verify stock for every line (before any write) --------
        for ci in cart_items:
            available = OrderService._available_stock(db, ci.product_id)
            if available < ci.quantity:
                raise InventoryError(
                    f"Insufficient stock for product {ci.product_id}: "
                    f"requested {ci.quantity}, available {available}."
                )

        # -------- 3. Decrement inventory rows --------
        # We consume from the "default" location first; multi-warehouse
        # allocation is a future enhancement.
        inventory_changes: list[tuple[Inventory, int, int]] = []
        for ci in cart_items:
            inv = db.execute(
                select(Inventory)
                .where(
                    Inventory.product_id == ci.product_id,
                    Inventory.location == "default",
                )
                .with_for_update()  # row-level lock prevents concurrent drain
            ).scalar_one_or_none()

            if inv is None:
                # Fall back to any location row (should not happen in practice).
                inv = db.execute(
                    select(Inventory)
                    .where(Inventory.product_id == ci.product_id)
                    .with_for_update()
                    .limit(1)
                ).scalar_one_or_none()

            if inv is None or inv.quantity < ci.quantity:
                # We already verified above, but the row-level lock plus
                # a concurrent checkout could have drained it. Treat as failure.
                raise InventoryError(f"Stock changed during checkout for product {ci.product_id}.")

            old_qty = inv.quantity
            inv.quantity = old_qty - ci.quantity
            inventory_changes.append((inv, old_qty, inv.quantity))

        # -------- 4. Create Order + OrderItems --------
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("0.00"),  # set below
            shipping_address=shipping_address,
            notes=notes,
        )
        db.add(order)
        db.flush()  # assigns order.id

        subtotals: list[Decimal] = []
        for ci in cart_items:
            product = ci.product  # eager-loaded via Cart.items relationship
            sub = multiply_money(ci.unit_price, ci.quantity)
            subtotals.append(sub)

            item = OrderItem(
                order_id=order.id,
                product_id=ci.product_id,
                product_name=product.name,
                product_sku=product.sku,
                quantity=ci.quantity,
                unit_price=ci.unit_price,
                subtotal=sub,
            )
            db.add(item)

        order.total_amount = sum_money(subtotals)

        # -------- 5. Clear cart items --------
        for ci in cart_items:
            db.delete(ci)

        # -------- 6. Commit — single atomic transaction --------
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("checkout_failed_rollback", user_id=user_id)
            raise

        # Reload with items for response
        order = OrderService.get_by_id(db, order.id)

        # -------- 7. Publish events (after commit) --------
        placed = OrderPlacedEvent(
            order_id=order.id,
            user_id=user_id,
            total_amount=order.total_amount,
            item_count=len(order.items),
        )
        await producer.publish("order.placed", placed, key=str(order.id))

        for inv, old_qty, new_qty in inventory_changes:
            ev = InventoryChangedEvent(
                product_id=inv.product_id,
                location=inv.location,
                old_quantity=old_qty,
                new_quantity=new_qty,
            )
            await producer.publish("inventory.changed", ev, key=str(inv.product_id))

        logger.info(
            "order_placed",
            order_id=order.id,
            user_id=user_id,
            total=str(order.total_amount),
            item_count=len(order.items),
        )
        return order

    # ------------------------------------------------------------------
    # Cancel
    # ------------------------------------------------------------------
    @staticmethod
    async def cancel(
        db: Session,
        producer: KafkaProducer,
        *,
        order_id: int,
        acting_user_id: int,
        is_admin: bool,
        reason: str | None = None,
    ) -> Order:
        """Cancel a PENDING or PAID order; restore inventory."""
        order = OrderService.get_by_id(db, order_id)

        if not is_admin and order.user_id != acting_user_id:
            # Pretend not found — don't leak existence to non-owners.
            raise NotFoundError(f"Order {order_id} not found.")

        if order.status not in (OrderStatus.PENDING, OrderStatus.PAID):
            raise ConflictError(f"Cannot cancel order in status {order.status.value!r}.")

        # Restore inventory
        restored: list[tuple[Inventory, int, int]] = []
        for item in order.items:
            # product_id is non-nullable (FK RESTRICT); if a product row
            # was ever deleted, MySQL would have blocked that delete.
            inv = db.execute(
                select(Inventory)
                .where(
                    Inventory.product_id == item.product_id,
                    Inventory.location == "default",
                )
                .with_for_update()
            ).scalar_one_or_none()

            if inv is None:
                inv = db.execute(
                    select(Inventory)
                    .where(Inventory.product_id == item.product_id)
                    .with_for_update()
                    .limit(1)
                ).scalar_one_or_none()

            if inv is None:
                # No inventory row (product never had stock tracked).
                # Nothing to restore — log and continue.
                logger.warning(
                    "cancel_missing_inventory_row",
                    order_id=order_id,
                    product_id=item.product_id,
                )
                continue

            old_qty = inv.quantity
            inv.quantity = old_qty + item.quantity
            restored.append((inv, old_qty, inv.quantity))

        order.status = OrderStatus.CANCELLED

        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("order_cancel_failed_rollback", order_id=order_id)
            raise

        order = OrderService.get_by_id(db, order_id)

        cancelled = OrderCancelledEvent(
            order_id=order.id,
            user_id=order.user_id,
            reason=reason,
        )
        await producer.publish("order.cancelled", cancelled, key=str(order.id))

        for inv, old_qty, new_qty in restored:
            ev = InventoryChangedEvent(
                product_id=inv.product_id,
                location=inv.location,
                old_quantity=old_qty,
                new_quantity=new_qty,
            )
            await producer.publish("inventory.changed", ev, key=str(inv.product_id))

        logger.info(
            "order_cancelled",
            order_id=order.id,
            acting_user_id=acting_user_id,
            by_admin=is_admin,
        )
        return order

    # ------------------------------------------------------------------
    # Admin: change status
    # ------------------------------------------------------------------
    @staticmethod
    async def change_status(
        db: Session,
        producer: KafkaProducer,
        *,
        order_id: int,
        new_status: OrderStatus,
        reason: str | None = None,
    ) -> Order:
        """Advance an order through its lifecycle, enforcing legal transitions."""
        order = OrderService.get_by_id(db, order_id)

        if new_status == order.status:
            return order

        allowed = _ALLOWED_TRANSITIONS.get(order.status, set())
        if new_status not in allowed:
            raise ConflictError(
                f"Cannot transition from {order.status.value!r} to {new_status.value!r}."
            )

        # Route cancel through the cancel service for inventory restore.
        if new_status == OrderStatus.CANCELLED:
            return await OrderService.cancel(
                db,
                producer,
                order_id=order_id,
                acting_user_id=order.user_id,
                is_admin=True,
                reason=reason,
            )

        order.status = new_status
        db.commit()
        order = OrderService.get_by_id(db, order_id)

        logger.info(
            "order_status_changed",
            order_id=order.id,
            new_status=new_status.value,
        )
        return order

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _available_stock(db: Session, product_id: int) -> int:
        """Sum of Inventory.quantity across all locations for a product."""
        qty = db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.product_id == product_id
            )
        ).scalar_one()
        return int(qty)
