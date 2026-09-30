"""Pydantic v2 schemas for orders."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from shopify_cart.models.order import OrderStatus


# ----------------------------------------------------------------------
# Requests
# ----------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    shipping_address: str = Field(min_length=5, max_length=500)
    notes: str | None = Field(default=None, max_length=1000)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    reason: str | None = Field(default=None, max_length=255)


class OrderCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


# ----------------------------------------------------------------------
# Responses
# ----------------------------------------------------------------------
class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    product_name: str
    product_sku: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    notes: str | None
    items: list[OrderItemRead] = Field(default_factory=list)
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
