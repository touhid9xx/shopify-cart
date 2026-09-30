"""Pydantic v2 schemas for inventory."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


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


class InventoryRead(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime
    is_low_stock: bool
