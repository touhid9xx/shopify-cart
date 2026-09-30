"""Order ORM model — immutable record of a checkout."""

from __future__ import annotations

import enum
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.order_item import OrderItem
    from shopify_cart.models.user import User


class OrderStatus(str, enum.Enum):
    """Order lifecycle. Immutable in DB via string enum."""

    PENDING = "pending"  # created, awaiting payment
    PAID = "paid"  # payment received (stub — no real payment gateway)
    SHIPPED = "shipped"  # dispatched
    DELIVERED = "delivered"  # handed over
    CANCELLED = "cancelled"  # user/admin cancelled before ship


class Order(Base, TimestampMixin):
    """
    A placed order.

    Amounts are snapshotted — later product/price changes do NOT
    alter historical orders.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[OrderStatus] = mapped_column(
        SAEnum(OrderStatus, name="order_status_enum", native_enum=False, length=20),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(String(500), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    user: Mapped[User] = relationship("User")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItem.id",
    )

    def __repr__(self) -> str:
        return (
            f"<Order id={self.id} user_id={self.user_id} "
            f"status={self.status.value} total={self.total_amount}>"
        )
