"""Inventory ORM model — quantity per (product, location)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.product import Product


class Inventory(Base, TimestampMixin):
    """
    Stock level for a product at a specific warehouse location.

    We allow multiple rows per product (one per location) so that
    `quantity` is unambiguous — never mix stock across warehouses.
    """

    __tablename__ = "inventories"

    __table_args__ = (
        UniqueConstraint("product_id", "location", name="uq_inventory_product_location"),
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_inventory_threshold_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location: Mapped[str] = mapped_column(String(80), nullable=False, default="default")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=5)

    # ---------- Relationships ----------
    product: Mapped[Product] = relationship(
        "Product",
        back_populates="inventories",
    )

    def __repr__(self) -> str:
        return (
            f"<Inventory id={self.id} product_id={self.product_id} "
            f"loc={self.location!r} qty={self.quantity}>"
        )

    @property
    def is_low_stock(self) -> bool:
        """True when quantity is at or below the low-stock threshold."""
        return self.quantity <= self.low_stock_threshold
