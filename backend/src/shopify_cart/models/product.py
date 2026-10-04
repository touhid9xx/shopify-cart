# shopify_cart/models/product.py
"""Product ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.category import Category
    from shopify_cart.models.inventory import Inventory
    from shopify_cart.models.user import User


class ProductReviewStatus(StrEnum):
    """Review lifecycle for ML-categorized products."""

    PENDING = "pending"  # awaiting admin review
    APPROVED = "approved"  # admin confirmed
    REJECTED = "rejected"  # admin rejected


class Product(Base, TimestampMixin):
    """
    A sellable product.

    `price` is Decimal(10, 2) — money must never be float.
    `category_id` is nullable because ML auto-categorization may fail
    (low confidence) → product lands in "needs review" state.
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # ---------- Review workflow ----------
    review_status: Mapped[ProductReviewStatus] = mapped_column(
        SAEnum(
            ProductReviewStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],  # ← ADD THIS LINE
        ),
        default=ProductReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---------- ML metadata ----------
    ml_category_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ml_confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)

    # ---------- Relationships ----------
    category: Mapped[Category | None] = relationship(
        "Category",
        back_populates="products",
    )
    inventories: Mapped[list[Inventory]] = relationship(
        "Inventory",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    reviewer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )

    def __repr__(self) -> str:
        return (
            f"<Product id={self.id} sku={self.sku!r} "
            f"price={self.price} status={self.review_status}>"
        )
