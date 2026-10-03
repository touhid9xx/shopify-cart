# shopify_cart/schemas/order.py
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shopify_cart.models.order import OrderStatus


# ══════════════════════════════════════════════════════════════════════
# Nested / read models
# ══════════════════════════════════════════════════════════════════════
class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderRead(BaseModel):
    """Customer-facing order payload — no admin-only fields."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    notes: str | None = None

    items: list[OrderItemRead] = Field(default_factory=list)
    item_count: int = 0

    created_at: datetime
    updated_at: datetime


class OrderReadAdmin(OrderRead):
    """Admin-facing order payload — includes review metadata."""

    admin_message: str | None = None
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None


# ══════════════════════════════════════════════════════════════════════
# Write / request payloads
# ══════════════════════════════════════════════════════════════════════
class CheckoutRequest(BaseModel):
    """Payload for POST /orders/checkout."""

    shipping_address: str = Field(min_length=1, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)


class OrderCancelRequest(BaseModel):
    """Payload for POST /orders/{id}/cancel."""

    reason: str | None = Field(default=None, max_length=500)


class OrderStatusUpdate(BaseModel):
    """Payload for PATCH /admin/orders/{id}/status."""

    status: OrderStatus
    reason: str | None = Field(default=None, max_length=2000)
