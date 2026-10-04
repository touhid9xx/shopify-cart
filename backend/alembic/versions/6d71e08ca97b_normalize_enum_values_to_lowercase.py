"""normalize enum values to lowercase (StrEnum values)

Revision ID: 6d71e08ca97b
Revises: 0373d38e92b0
Create Date: 2026-10-04

Why:
    SQLAlchemy `SAEnum(SomeStrEnum, native_enum=False)` without
    `values_callable` stores enum NAMES (UPPERCASE) rather than VALUES
    (lowercase). After adding `values_callable`, ORM queries filter on
    lowercase but existing rows are UPPERCASE → need one-time
    normalization.

Affects:
    - products.review_status   ('PENDING' → 'pending', etc.)
    - orders.status             ('CONFIRMED' → 'confirmed', etc.)
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6d71e08ca97b"
down_revision: Union[str, None] = "0373d38e92b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert uppercase enum NAMES to lowercase VALUES."""

    # ─────────────────────────────────────────────────────────────
    # products.review_status
    # ─────────────────────────────────────────────────────────────
    op.execute(
        "UPDATE products SET review_status = 'pending' "
        "WHERE review_status = 'PENDING'"
    )
    op.execute(
        "UPDATE products SET review_status = 'approved' "
        "WHERE review_status = 'APPROVED'"
    )
    op.execute(
        "UPDATE products SET review_status = 'rejected' "
        "WHERE review_status = 'REJECTED'"
    )

    # ─────────────────────────────────────────────────────────────
    # orders.status
    # ─────────────────────────────────────────────────────────────
    op.execute("UPDATE orders SET status = 'pending' WHERE status = 'PENDING'")
    op.execute("UPDATE orders SET status = 'confirmed' WHERE status = 'CONFIRMED'")
    op.execute("UPDATE orders SET status = 'paid' WHERE status = 'PAID'")
    op.execute("UPDATE orders SET status = 'shipped' WHERE status = 'SHIPPED'")
    op.execute("UPDATE orders SET status = 'delivered' WHERE status = 'DELIVERED'")
    op.execute("UPDATE orders SET status = 'cancelled' WHERE status = 'CANCELLED'")
    op.execute("UPDATE orders SET status = 'rejected' WHERE status = 'REJECTED'")


def downgrade() -> None:
    """Revert to uppercase enum NAMES."""

    # products.review_status
    op.execute(
        "UPDATE products SET review_status = 'PENDING' "
        "WHERE review_status = 'pending'"
    )
    op.execute(
        "UPDATE products SET review_status = 'APPROVED' "
        "WHERE review_status = 'approved'"
    )
    op.execute(
        "UPDATE products SET review_status = 'REJECTED' "
        "WHERE review_status = 'rejected'"
    )

    # orders.status
    op.execute("UPDATE orders SET status = 'PENDING' WHERE status = 'pending'")
    op.execute("UPDATE orders SET status = 'CONFIRMED' WHERE status = 'confirmed'")
    op.execute("UPDATE orders SET status = 'PAID' WHERE status = 'paid'")
    op.execute("UPDATE orders SET status = 'SHIPPED' WHERE status = 'shipped'")
    op.execute("UPDATE orders SET status = 'DELIVERED' WHERE status = 'delivered'")
    op.execute("UPDATE orders SET status = 'CANCELLED' WHERE status = 'cancelled'")
    op.execute("UPDATE orders SET status = 'REJECTED' WHERE status = 'rejected'")
