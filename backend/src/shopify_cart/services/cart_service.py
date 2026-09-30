"""Cart business logic — get-or-create, add, update, remove, clear, totals."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from shopify_cart.core.money import sum_money
from shopify_cart.exceptions import CartError, InventoryError, NotFoundError
from shopify_cart.kafka.events import (
    CartClearedEvent,
    CartItemAddedEvent,
    CartItemRemovedEvent,
    CartUpdatedEvent,
)
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.models.cart import Cart
from shopify_cart.models.cart_item import CartItem
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product

logger = get_logger(__name__)


class CartService:
    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    @staticmethod
    def get_or_create(db: Session, user_id: int) -> Cart:
        cart = db.execute(
            select(Cart).where(Cart.user_id == user_id).options(selectinload(Cart.items))
        ).scalar_one_or_none()
        if cart is not None:
            return cart

        cart = Cart(user_id=user_id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
        logger.info("cart_created", user_id=user_id, cart_id=cart.id)
        return cart

    @staticmethod
    def reload(db: Session, cart_id: int) -> Cart:
        cart = db.execute(
            select(Cart)
            .where(Cart.id == cart_id)
            .options(selectinload(Cart.items))
            .execution_options(populate_existing=True)
        ).scalar_one_or_none()
        if cart is None:
            raise NotFoundError(f"Cart {cart_id} not found.")
        return cart

    # ------------------------------------------------------------------
    # Stock helper
    # ------------------------------------------------------------------
    @staticmethod
    def available_stock(db: Session, product_id: int) -> int:
        qty = db.execute(
            select(func.coalesce(func.sum(Inventory.quantity), 0)).where(
                Inventory.product_id == product_id
            )
        ).scalar_one()
        return int(qty)

    # ------------------------------------------------------------------
    # Add item
    # ------------------------------------------------------------------
    @staticmethod
    async def add_item(
        db: Session,
        producer: KafkaProducer,
        *,
        user_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        if quantity <= 0:
            raise CartError("Quantity must be >= 1.")

        product = db.get(Product, product_id)
        if product is None or not product.is_active:
            raise NotFoundError(f"Product {product_id} not found or inactive.")

        cart = CartService.get_or_create(db, user_id)

        existing = db.execute(
            select(CartItem).where(
                CartItem.cart_id == cart.id,
                CartItem.product_id == product_id,
            )
        ).scalar_one_or_none()

        new_qty = (existing.quantity if existing else 0) + quantity
        available = CartService.available_stock(db, product_id)
        if new_qty > available:
            raise InventoryError(f"Only {available} unit(s) available for product {product_id}.")

        if existing is not None:
            existing.quantity = new_qty
        else:
            item = CartItem(
                cart_id=cart.id,
                product_id=product_id,
                quantity=quantity,
                unit_price=product.price,
            )
            db.add(item)

        db.commit()
        cart = CartService.reload(db, cart.id)

        # Events
        item_event = CartItemAddedEvent(
            cart_id=cart.id,
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=product.price,
        )
        await producer.publish("cart.item_added", item_event, key=str(cart.id))

        updated_event = CartUpdatedEvent(
            cart_id=cart.id,
            user_id=user_id,
            item_count=len(cart.items),
            total_amount=CartService.total_amount(cart),
        )
        await producer.publish("cart.updated", updated_event, key=str(cart.id))

        logger.info(
            "cart_item_added",
            user_id=user_id,
            cart_id=cart.id,
            product_id=product_id,
            quantity=quantity,
        )
        return cart

    # ------------------------------------------------------------------
    # Update item
    # ------------------------------------------------------------------
    @staticmethod
    async def update_item(
        db: Session,
        producer: KafkaProducer,
        *,
        user_id: int,
        item_id: int,
        quantity: int,
    ) -> Cart:
        cart = CartService.get_or_create(db, user_id)
        item = db.get(CartItem, item_id)
        if item is None or item.cart_id != cart.id:
            raise NotFoundError(f"Cart item {item_id} not found in your cart.")

        if quantity == 0:
            return await CartService.remove_item(db, producer, user_id=user_id, item_id=item_id)

        available = CartService.available_stock(db, item.product_id)
        if quantity > available:
            raise InventoryError(
                f"Only {available} unit(s) available for product {item.product_id}."
            )

        item.quantity = quantity
        db.commit()
        cart = CartService.reload(db, cart.id)

        updated_event = CartUpdatedEvent(
            cart_id=cart.id,
            user_id=user_id,
            item_count=len(cart.items),
            total_amount=CartService.total_amount(cart),
        )
        await producer.publish("cart.updated", updated_event, key=str(cart.id))

        logger.info(
            "cart_item_updated",
            user_id=user_id,
            cart_id=cart.id,
            item_id=item_id,
            quantity=quantity,
        )
        return cart

    # ------------------------------------------------------------------
    # Remove item
    # ------------------------------------------------------------------
    @staticmethod
    async def remove_item(
        db: Session,
        producer: KafkaProducer,
        *,
        user_id: int,
        item_id: int,
    ) -> Cart:
        cart = CartService.get_or_create(db, user_id)
        item = db.get(CartItem, item_id)
        if item is None or item.cart_id != cart.id:
            raise NotFoundError(f"Cart item {item_id} not found in your cart.")

        product_id = item.product_id
        db.delete(item)
        db.commit()
        cart = CartService.reload(db, cart.id)

        removed_event = CartItemRemovedEvent(
            cart_id=cart.id,
            user_id=user_id,
            product_id=product_id,
        )
        await producer.publish("cart.item_removed", removed_event, key=str(cart.id))

        updated_event = CartUpdatedEvent(
            cart_id=cart.id,
            user_id=user_id,
            item_count=len(cart.items),
            total_amount=CartService.total_amount(cart),
        )
        await producer.publish("cart.updated", updated_event, key=str(cart.id))

        logger.info(
            "cart_item_removed",
            user_id=user_id,
            cart_id=cart.id,
            item_id=item_id,
        )
        return cart

    # ------------------------------------------------------------------
    # Clear cart
    # ------------------------------------------------------------------
    @staticmethod
    async def clear(
        db: Session,
        producer: KafkaProducer,
        *,
        user_id: int,
    ) -> Cart:
        cart = CartService.get_or_create(db, user_id)
        removed = len(cart.items)
        for item in list(cart.items):
            db.delete(item)
        db.commit()
        cart = CartService.reload(db, cart.id)

        cleared_event = CartClearedEvent(
            cart_id=cart.id,
            user_id=user_id,
            removed_item_count=removed,
        )
        await producer.publish("cart.cleared", cleared_event, key=str(cart.id))

        updated_event = CartUpdatedEvent(
            cart_id=cart.id,
            user_id=user_id,
            item_count=0,
            total_amount=Decimal("0.00"),
        )
        await producer.publish("cart.updated", updated_event, key=str(cart.id))

        logger.info("cart_cleared", user_id=user_id, cart_id=cart.id, removed=removed)
        return cart

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------
    @staticmethod
    def total_amount(cart: Cart) -> Decimal:
        return sum_money([item.subtotal for item in cart.items])
