# shopify_cart/models/order.py
"""Order ORM model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.order_item import OrderItem
    from shopify_cart.models.user import User


class OrderStatus(StrEnum):
    PENDING = "pending"  # customer placed, awaiting admin
    CONFIRMED = "confirmed"  # admin accepted
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"  # customer cancelled
    REJECTED = "rejected"  # admin rejected


class Order(Base, TimestampMixin):
    """
    A customer order.

    `user_id` is the customer; `reviewed_by` is the admin who approved or
    rejected the order. Both point to users.id, so every User relationship
    must declare which FK it uses.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(
            OrderStatus,
            native_enum=False,
            length=20,
            values_callable=lambda e: [m.value for m in e],  # ← ADD THIS
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ---------- Admin review ----------
    admin_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # ---------- Relationships ----------
    # Both relationships target User, but via different FKs → disambiguate.
    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="orders",
    )
    reviewer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reviewed_by],
    )
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} user_id={self.user_id} "
            f"status={self.status} total={self.total_amount}>"
        )
