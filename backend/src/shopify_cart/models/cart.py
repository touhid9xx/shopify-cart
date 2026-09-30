"""Cart ORM model — one active cart per user."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.cart_item import CartItem
    from shopify_cart.models.user import User


class Cart(Base, TimestampMixin):
    """
    One cart per user (enforced by unique constraint on user_id).

    We keep carts long-lived — items can be updated, cleared, but
    the cart row persists so we can track history & timestamps.
    """

    __tablename__ = "carts"
    __table_args__ = (UniqueConstraint("user_id", name="uq_cart_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship("User")
    items: Mapped[list[CartItem]] = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan",
        order_by="CartItem.id",
    )

    def __repr__(self) -> str:
        return f"<Cart id={self.id} user_id={self.user_id}>"
