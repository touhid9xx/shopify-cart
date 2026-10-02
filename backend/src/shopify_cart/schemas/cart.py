"""Pydantic v2 schemas for cart."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Requests
# ----------------------------------------------------------------------
class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(default=1, ge=1, le=999)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=0, le=999)  # 0 → remove item


# ----------------------------------------------------------------------
# Responses
# ----------------------------------------------------------------------
class CartItemRead(BaseModel):
    """Cart item WITHOUT embedded product — kept for backward compat."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    created_at: datetime
    updated_at: datetime


class CartItemProductSnapshot(BaseModel):
    """Minimal product info embedded in cart item responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    sku: str
    price: Decimal
    image_url: str | None = None
    is_active: bool


class CartItemReadWithProduct(CartItemRead):
    """Cart item WITH embedded product snapshot."""

    product: CartItemProductSnapshot


class CartRead(BaseModel):
    """Legacy cart read — kept for backward compat."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    items: list[CartItemRead] = Field(default_factory=list)
    item_count: int = 0
    total_quantity: int = 0
    total_amount: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime


class CartReadWithProducts(BaseModel):
    """Cart response with each item embedding its product."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    items: list[CartItemReadWithProduct] = Field(default_factory=list)
    item_count: int = 0
    total_quantity: int = 0
    total_amount: Decimal = Decimal("0.00")
    created_at: datetime
    updated_at: datetime
