"""Pydantic v2 schemas for inventory."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Base / write schemas
# ----------------------------------------------------------------------
class InventoryBase(BaseModel):
    location: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


class InventoryCreate(InventoryBase):
    product_id: int


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)


class InventoryAdjust(BaseModel):
    """Increment/decrement payload — used by admin PATCH endpoint."""

    delta: int = Field(description="Positive to add stock, negative to remove.")
    reason: str | None = Field(default=None, max_length=255)


# ----------------------------------------------------------------------
# Read schemas
# ----------------------------------------------------------------------
class InventoryRead(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool


class ProductSnapshot(BaseModel):
    """Compact product info embedded in inventory rows (for admin tables)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    image_url: str | None = None
    price: Decimal
    is_active: bool
    review_status: str  # ProductReviewStatus value


class InventoryWithProduct(InventoryRead):
    """Inventory row with embedded product snapshot for admin UI."""

    product: ProductSnapshot


# ----------------------------------------------------------------------
# Stats / KPIs
# ----------------------------------------------------------------------
class InventoryStats(BaseModel):
    """Aggregated KPIs for the admin inventory dashboard."""

    total_skus: int = Field(description="Distinct products with inventory records")
    total_units: int = Field(description="Sum of quantity across all locations")
    low_stock_count: int = Field(description="Rows where quantity <= threshold")
    out_of_stock_count: int = Field(description="Rows where quantity == 0")
    total_inventory_value: Decimal = Field(
        description="Sum of (quantity * product.price) across all rows"
    )
