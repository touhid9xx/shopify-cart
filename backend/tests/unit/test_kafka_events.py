from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from shopify_cart.kafka.events import (
    CartUpdatedEvent,
    InventoryLowEvent,
    OrderPlacedEvent,
    ProductCreatedEvent,
    Topics,
)


def test_topics_all_unique() -> None:
    assert len(Topics.ALL) == len(set(Topics.ALL))


def test_product_created_event_serializes() -> None:
    e = ProductCreatedEvent(
        product_id=1,
        name="Blue Shirt",
        sku="SHIRT-001",
        price=Decimal("19.99"),
        image_url="/images/blue-shirt.jpg",
    )
    data = e.model_dump(mode="json")
    assert data["topic"] == "product.created"
    assert data["product_id"] == 1
    assert data["price"] == "19.99"  # Decimal -> str in JSON mode
    assert "event_id" in data
    assert "occurred_at" in data


def test_event_is_frozen() -> None:
    e = ProductCreatedEvent(
        product_id=1,
        name="X",
        sku="X-1",
        price=Decimal("1.00"),
    )
    with pytest.raises(PydanticValidationError):
        # frozen=True means we cannot mutate
        e.product_id = 2  # type: ignore[misc]


def test_cart_updated_event() -> None:
    e = CartUpdatedEvent(
        cart_id=10,
        user_id=5,
        item_count=3,
        total_amount=Decimal("59.97"),
    )
    assert e.topic == "cart.updated"


def test_order_placed_event() -> None:
    e = OrderPlacedEvent(
        order_id=100,
        user_id=5,
        total_amount=Decimal("59.97"),
        item_count=3,
    )
    assert e.topic == "order.placed"


def test_inventory_low_event() -> None:
    e = InventoryLowEvent(
        product_id=1,
        location="WH-1",
        quantity=2,
        threshold=5,
    )
    assert e.topic == "inventory.low"
