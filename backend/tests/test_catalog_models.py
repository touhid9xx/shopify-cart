"""Unit tests for catalog models — pure schema, no DB."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError as PydanticValidationError

from shopify_cart.schemas.category import CategoryCreate, CategoryRead
from shopify_cart.schemas.inventory import InventoryAdjust, InventoryCreate
from shopify_cart.schemas.product import ProductCreate, ProductUpdate


# ----------------------------------------------------------------------
# Category
# ----------------------------------------------------------------------
def test_category_slug_lowercase_only() -> None:
    with pytest.raises(PydanticValidationError):
        CategoryCreate(name="Shirt", slug="SHIRT")  # uppercase not allowed


def test_category_slug_with_hyphen() -> None:
    c = CategoryCreate(name="T-Shirt", slug="t-shirt")
    assert c.slug == "t-shirt"


def test_category_parent_id_optional() -> None:
    c = CategoryCreate(name="Clothing", slug="clothing")
    assert c.parent_id is None


# ----------------------------------------------------------------------
# Product
# ----------------------------------------------------------------------
def test_product_price_must_be_positive() -> None:
    with pytest.raises(PydanticValidationError):
        ProductCreate(name="X", sku="X-1", price=Decimal("0"))


def test_product_price_two_decimals() -> None:
    with pytest.raises(PydanticValidationError):
        ProductCreate(name="X", sku="X-1", price=Decimal("19.999"))


def test_product_valid() -> None:
    p = ProductCreate(name="Blue Shirt", sku="SHIRT-001", price=Decimal("19.99"))
    assert p.price == Decimal("19.99")
    assert p.is_active is True
    assert p.category_id is None


def test_product_update_all_optional() -> None:
    u = ProductUpdate()
    assert u.name is None
    assert u.price is None


# ----------------------------------------------------------------------
# Inventory
# ----------------------------------------------------------------------
def test_inventory_quantity_non_negative() -> None:
    with pytest.raises(PydanticValidationError):
        InventoryCreate(product_id=1, location="WH-1", quantity=-1)


def test_inventory_threshold_default() -> None:
    inv = InventoryCreate(product_id=1, location="WH-1", quantity=10)
    assert inv.low_stock_threshold == 5


def test_inventory_adjust_allows_negative_delta() -> None:
    a = InventoryAdjust(delta=-5, reason="damaged")
    assert a.delta == -5
    assert a.reason == "damaged"


# ----------------------------------------------------------------------
# ORM model metadata (no DB)
# ----------------------------------------------------------------------
def test_category_table_name() -> None:
    from shopify_cart.models.category import Category

    assert Category.__tablename__ == "categories"


def test_product_table_name() -> None:
    from shopify_cart.models.product import Product

    assert Product.__tablename__ == "products"


def test_inventory_table_name() -> None:
    from shopify_cart.models.inventory import Inventory

    assert Inventory.__tablename__ == "inventories"


def test_inventory_is_low_stock_property() -> None:
    from shopify_cart.models.inventory import Inventory

    inv = Inventory(product_id=1, location="WH-1", quantity=3, low_stock_threshold=5)
    assert inv.is_low_stock is True

    inv.quantity = 5
    assert inv.is_low_stock is True  # at threshold

    inv.quantity = 6
    assert inv.is_low_stock is False


def test_category_read_from_attributes() -> None:
    """Make sure from_attributes=True works on CategoryRead."""
    assert CategoryRead.model_config.get("from_attributes") is True
