"""Pydantic v2 schemas for products."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Category (compact — embedded inside product reads)
# ----------------------------------------------------------------------
class CategoryRead(BaseModel):
    """Minimal category representation embedded in product payloads."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ----------------------------------------------------------------------
# Product — base / create / update
# ----------------------------------------------------------------------
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sku: str = Field(min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=10_000)
    price: Decimal = Field(gt=0, le=Decimal("99999999.99"), decimal_places=2)
    category_id: int | None = None
    image_url: str | None = Field(default=None, max_length=512)
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    sku: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=10_000)
    price: Decimal | None = Field(
        default=None,
        gt=0,
        le=Decimal("99999999.99"),
        decimal_places=2,
    )
    category_id: int | None = None
    image_url: str | None = Field(default=None, max_length=512)
    is_active: bool | None = None


# ----------------------------------------------------------------------
# Product — read (public API)
# ----------------------------------------------------------------------
class ProductRead(ProductBase):
    """
    Public product representation.

    `category` is included as a nested object — populated by the API's
    eager-loaded relationship (``selectinload(Product.category)``).
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    category: CategoryRead | None = None  # ← ADDED
    created_at: datetime
    updated_at: datetime


class ProductReadWithStock(ProductRead):
    """Product plus total available stock across all locations."""

    total_quantity: int = 0
