# src/shopify_cart/models/user.py
"""User ORM model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shopify_cart.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from shopify_cart.models.order import Order


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)


    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )


    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, server_default="1"
    )


    full_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    # ---------- Relationships ----------
    orders: Mapped[list[Order]] = relationship(
        "Order",
        foreign_keys="Order.user_id",
        back_populates="user",
    )
