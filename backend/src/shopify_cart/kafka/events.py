from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _new_event_id() -> str:
    return str(uuid.uuid4())


class BaseEvent(BaseModel):
    """Common fields every Kafka event carries."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(default_factory=_new_event_id)
    occurred_at: datetime = Field(default_factory=_now_utc)
    version: int = 1


# ---------------------------------------------------------------
# Topic names — single source of truth
# ---------------------------------------------------------------
class Topics:
    PRODUCT_CREATED = "product.created"
    PRODUCT_UPDATED = "product.updated"
    PRODUCT_DELETED = "product.deleted"
    INVENTORY_CHANGED = "inventory.changed"
    INVENTORY_LOW = "inventory.low"

    CART_UPDATED = "cart.updated"
    CART_ITEM_ADDED = "cart.item_added"
    CART_ITEM_REMOVED = "cart.item_removed"
    CART_CLEARED = "cart.cleared"

    ORDER_PLACED = "order.placed"
    ORDER_CANCELLED = "order.cancelled"

    ALL: tuple[str, ...] = (
        PRODUCT_CREATED,
        PRODUCT_UPDATED,
        PRODUCT_DELETED,
        INVENTORY_CHANGED,
        INVENTORY_LOW,
        CART_UPDATED,
        CART_ITEM_ADDED,
        CART_ITEM_REMOVED,
        CART_CLEARED,
        ORDER_PLACED,
        ORDER_CANCELLED,
    )


# ---------------------------------------------------------------
# Event schemas
# ---------------------------------------------------------------
class ProductCreatedEvent(BaseEvent):
    topic: Literal["product.created"] = "product.created"
    product_id: int
    name: str
    sku: str
    category_id: int | None = None
    price: Decimal
    image_url: str | None = None


class ProductUpdatedEvent(BaseEvent):
    topic: Literal["product.updated"] = "product.updated"
    product_id: int
    changed_fields: list[str] = Field(default_factory=list)


class ProductDeletedEvent(BaseEvent):
    topic: Literal["product.deleted"] = "product.deleted"
    product_id: int


class InventoryChangedEvent(BaseEvent):
    topic: Literal["inventory.changed"] = "inventory.changed"
    product_id: int
    location: str
    old_quantity: int
    new_quantity: int


class InventoryLowEvent(BaseEvent):
    topic: Literal["inventory.low"] = "inventory.low"
    product_id: int
    location: str
    quantity: int
    threshold: int


class CartUpdatedEvent(BaseEvent):
    topic: Literal["cart.updated"] = "cart.updated"
    cart_id: int
    user_id: int
    item_count: int
    total_amount: Decimal


class OrderPlacedEvent(BaseEvent):
    topic: Literal["order.placed"] = "order.placed"
    order_id: int
    user_id: int
    total_amount: Decimal
    item_count: int


class OrderCancelledEvent(BaseEvent):
    topic: Literal["order.cancelled"] = "order.cancelled"
    order_id: int
    user_id: int
    reason: str | None = None


class CartItemAddedEvent(BaseEvent):
    topic: Literal["cart.item_added"] = "cart.item_added"
    cart_id: int
    user_id: int
    product_id: int
    quantity: int
    unit_price: Decimal


class CartItemRemovedEvent(BaseEvent):
    topic: Literal["cart.item_removed"] = "cart.item_removed"
    cart_id: int
    user_id: int
    product_id: int


class CartClearedEvent(BaseEvent):
    topic: Literal["cart.cleared"] = "cart.cleared"
    cart_id: int
    user_id: int
    removed_item_count: int


EventType = (
    ProductCreatedEvent
    | ProductUpdatedEvent
    | ProductDeletedEvent
    | InventoryChangedEvent
    | InventoryLowEvent
    | CartUpdatedEvent
    | CartItemAddedEvent
    | CartItemRemovedEvent
    | CartClearedEvent
    | OrderPlacedEvent
    | OrderCancelledEvent
)
