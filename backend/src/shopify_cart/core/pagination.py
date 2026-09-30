"""Reusable pagination helpers — query params + response envelope."""

from __future__ import annotations

from typing import Annotated, Any, Generic, TypeVar, cast

from fastapi import Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

T = TypeVar("T")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PageParams(BaseModel):
    """Query params for any paginated endpoint."""

    page: int = Field(default=1, ge=1)
    size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def get_page_params(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description=f"Items per page (max {MAX_PAGE_SIZE})"),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    """FastAPI dependency that parses + validates pagination query params."""
    return PageParams(page=page, size=size)


class Page(BaseModel, Generic[T]):
    """Standard paginated response envelope."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int


def paginate_query(
    db: Session,
    stmt: Select[Any],
    params: PageParams,
) -> tuple[list[T], int]:
    """Execute `stmt` with LIMIT/OFFSET and return (rows, total).

    The Select type is `Select[Any]` because SQLAlchemy's generic
    propagation through `.scalars().all()` doesn't tell mypy that
    `tuple[T]` unwraps to `T`. We cast at the end.

    Returns:
        (rows, total) — total is the count of rows matching the WHERE clause
        (ignoring limit/offset).
    """
    # Count total rows matching the same WHERE clause
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total: int = db.execute(count_stmt).scalar_one()

    result = db.execute(stmt.limit(params.size).offset(params.offset))
    rows: list[T] = list(cast("list[T]", result.scalars().all()))

    return rows, total


def build_page(items: list[T], total: int, params: PageParams) -> Page[T]:
    """Wrap items + total into a Page envelope."""
    pages = (total + params.size - 1) // params.size if params.size else 0
    return Page[T](
        items=items,
        total=total,
        page=params.page,
        size=params.size,
        pages=pages,
    )
