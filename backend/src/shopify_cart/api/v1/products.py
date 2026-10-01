"""Public product endpoints — browse, filter, detail."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shopify_cart.api.deps import DbSession
from shopify_cart.core.pagination import (
    Page,
    PageParams,
    build_page,
    get_page_params,
    paginate_query,
)
from shopify_cart.exceptions import NotFoundError
from shopify_cart.models.product import Product
from shopify_cart.schemas.product import ProductRead, ProductReadWithStock

router = APIRouter(prefix="/products", tags=["products"])


# ----------------------------------------------------------------------
# List — paginated, filterable, searchable
# ----------------------------------------------------------------------
@router.get("", response_model=Page[ProductRead])
def list_products(
    db: DbSession,
    params: Annotated[PageParams, Depends(get_page_params)],
    category_id: Annotated[int | None, Query(description="Filter by category")] = None,
    q: Annotated[str | None, Query(description="Search name/sku", max_length=100)] = None,
    active_only: Annotated[bool, Query()] = True,
) -> Page[ProductRead]:
    # Eager-load `category` to avoid N+1 queries when serializing
    # ProductRead (which exposes product.category.name).
    stmt = select(Product).options(selectinload(Product.category))

    if active_only:
        stmt = stmt.where(Product.is_active.is_(True))
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Product.name.like(like)) | (Product.sku.like(like)))

    stmt = stmt.order_by(Product.created_at.desc())

    # Annotate the tuple result so mypy can infer element type.
    result: tuple[list[Product], int] = paginate_query(db, stmt, params)
    rows, total = result

    return build_page([ProductRead.model_validate(r) for r in rows], total, params)


# ----------------------------------------------------------------------
# Detail — single product with stock + category
# ----------------------------------------------------------------------
@router.get("/{product_id}", response_model=ProductReadWithStock)
def get_product(db: DbSession, product_id: int) -> ProductReadWithStock:
    product = db.execute(
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.category),
            selectinload(Product.inventories),
        )
    ).scalar_one_or_none()

    if product is None:
        raise NotFoundError(f"Product {product_id} not found.")

    total_qty = sum(inv.quantity for inv in product.inventories)
    base = ProductRead.model_validate(product)
    return ProductReadWithStock(
        **base.model_dump(),
        total_quantity=total_qty,
    )
