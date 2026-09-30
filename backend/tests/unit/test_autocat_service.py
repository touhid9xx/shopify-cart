from __future__ import annotations

import io
from collections.abc import Iterator
from typing import cast

import pytest
from PIL import Image
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from shopify_cart.db.base import Base
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (64, 64), color=(120, 200, 80))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------
# Fixture — in-memory DB
# ----------------------------------------------------------------------
@pytest.fixture
def in_memory_db() -> Iterator[Session]:
    """
    SQLite in-memory DB with only the tables we need.

    Note: cast(Table, ...) is required because SQLAlchemy's type stubs
    declare DeclarativeBase.__table__ as FromClause, but at runtime it
    is always a Table.
    """
    engine = create_engine("sqlite:///:memory:")

    tables = [
        cast(Table, Category.__table__),
        cast(Table, Product.__table__),
        cast(Table, Inventory.__table__),
    ]

    Base.metadata.create_all(engine, tables=tables)

    test_session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = test_session_factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
