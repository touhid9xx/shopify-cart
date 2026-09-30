"""Analytics + alert tables written by Kafka consumers."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.product import Product


class DailySales(Base, TimestampMixin):
    """
    Aggregated sales per (date, product).

    Upserted on every `order.placed` event — consumers increment
    quantity + revenue instead of inserting a row per order line,
    which keeps the table small and queries fast.
    """

    __tablename__ = "daily_sales"
    __table_args__ = (
        UniqueConstraint("sales_date", "product_id", name="uq_daily_sales_date_product"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sales_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0.00")
    )
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    product: Mapped[Product] = relationship("Product")

    def __repr__(self) -> str:
        return (
            f"<DailySales {self.sales_date} product_id={self.product_id} "
            f"qty={self.quantity} revenue={self.revenue}>"
        )


class ProductView(Base, TimestampMixin):
    """Raw view events — reserved for future product detail tracking."""

    __tablename__ = "product_views"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)


class InventoryAlert(Base, TimestampMixin):
    """
    Raised by the `inventory.low` consumer. Admin UI lists unresolved
    alerts. `resolved_at` set when admin acknowledges.
    """

    __tablename__ = "inventory_alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    @property
    def is_resolved(self) -> bool:
        return self.resolved_at is not None
