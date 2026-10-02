"""Public category endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from shopify_cart.api.deps import DbSession
from shopify_cart.core.pagination import (
    Page,
    PageParams,
    build_page,
    get_page_params,
    paginate_query,
)
from shopify_cart.exceptions import NotFoundError
from shopify_cart.models.category import Category
from shopify_cart.schemas.category import CategoryRead, CategoryTreeNode

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=Page[CategoryRead])
def list_categories(
    db: DbSession,
    params: Annotated[PageParams, Depends(get_page_params)],
) -> Page[CategoryRead]:
    stmt = select(Category).order_by(Category.name.asc())
    # Annotate the tuple result so mypy can infer element type.
    result: tuple[list[Category], int] = paginate_query(db, stmt, params)
    rows, total = result
    return build_page([CategoryRead.model_validate(r) for r in rows], total, params)


@router.get("/tree", response_model=list[CategoryTreeNode])
def category_tree(db: DbSession) -> list[CategoryTreeNode]:
    """Return full hierarchy as a nested tree of roots."""

    all_cats = list(
        db.execute(select(Category).order_by(Category.name.asc())).scalars().all()
    )

    # ── Step 1: create a fresh node per category — no model_validate ──
    by_id: dict[int, CategoryTreeNode] = {}
    for c in all_cats:
        by_id[c.id] = CategoryTreeNode(
            id=c.id,
            name=c.name,
            slug=c.slug,
            parent_id=c.parent_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
            children=[],   # ← explicit — never shared, never cached
        )

    # ── Step 2: attach children exactly once ──
    roots: list[CategoryTreeNode] = []
    for c in all_cats:
        node = by_id[c.id]
        if c.parent_id is None:
            roots.append(node)
        else:
            parent = by_id.get(c.parent_id)
            if parent is not None:
                parent.children.append(node)

    return roots


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(db: DbSession, category_id: int) -> CategoryRead:
    cat = db.get(Category, category_id)
    if cat is None:
        raise NotFoundError(f"Category {category_id} not found.")
    return CategoryRead.model_validate(cat)
