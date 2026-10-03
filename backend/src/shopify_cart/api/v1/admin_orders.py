# src/shopify_cart/api/v1/admin_orders.py
"""Admin order endpoints — list all, change status, accept/reject/ship."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.core.pagination import (
    Page,
    PageParams,
    build_page,
    get_page_params,
    paginate_query,
)
from shopify_cart.exceptions import ConflictError, NotFoundError
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.models.order import Order, OrderStatus
from shopify_cart.schemas.order import (
    OrderItemRead,
    OrderReadAdmin,
    OrderStatusUpdate,
)
from shopify_cart.services.order_service import OrderService

router = APIRouter(prefix="/admin/orders", tags=["admin:orders"])
logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Dependency helpers
# ══════════════════════════════════════════════════════════════════════
def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


# ══════════════════════════════════════════════════════════════════════
# Request schemas (local to this router)
# ══════════════════════════════════════════════════════════════════════
class OrderActionPayload(BaseModel):
    """Optional notes for accept."""

    notes: str | None = Field(default=None, max_length=2000)


class OrderRejectPayload(BaseModel):
    """Required reason for rejection."""

    reason: str = Field(min_length=3, max_length=500)


# ══════════════════════════════════════════════════════════════════════
# Serializer — admin view
# ══════════════════════════════════════════════════════════════════════
def _to_read(order: Order) -> OrderReadAdmin:
    """Convert an Order ORM row to OrderReadAdmin, loading items."""
    items = [OrderItemRead.model_validate(i) for i in order.items]
    return OrderReadAdmin(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        notes=order.notes,
        items=items,
        item_count=len(items),
        # ── Admin-only fields ──
        admin_message=order.admin_message,
        reviewed_by=order.reviewed_by,
        reviewed_at=order.reviewed_at,
        # ── Timestamps ──
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


# ══════════════════════════════════════════════════════════════════════
# List
# ══════════════════════════════════════════════════════════════════════
@router.get("", response_model=Page[OrderReadAdmin])
def list_all_orders(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> Page[OrderReadAdmin]:
    """Paginated list of all orders, optionally filtered by status."""
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Order.status == status_filter)

    rows: list[Order]
    total: int
    rows, total = paginate_query(db, stmt, params)
    return build_page([_to_read(o) for o in rows], total, params)


# ══════════════════════════════════════════════════════════════════════
# Generic status change
# ══════════════════════════════════════════════════════════════════════
@router.patch(
    "/{order_id}/status",
    response_model=OrderReadAdmin,
    summary="Change order status (admin only)",
)
async def change_status(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    order_id: int,
    payload: OrderStatusUpdate,
) -> OrderReadAdmin:
    """Low-level status transition. Prefer /accept, /reject, /ship for
    business-meaningful actions with proper side effects."""
    order = await OrderService.change_status(
        db,
        producer,
        order_id=order_id,
        new_status=payload.status,
        reason=payload.reason,
    )
    return _to_read(order)


# ══════════════════════════════════════════════════════════════════════
# Accept — PENDING → CONFIRMED
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/{order_id}/accept",
    response_model=OrderReadAdmin,
    summary="Accept a pending order",
)
async def accept_order(
    db: DbSession,
    admin: CurrentAdmin,
    order_id: int,
    payload: OrderActionPayload | None = None,
) -> OrderReadAdmin:
    """Accept a pending order, marking it CONFIRMED."""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found.")
    if order.status != OrderStatus.PENDING:
        raise ConflictError(f"Order {order_id} is not pending (current: {order.status}).")

    order.status = OrderStatus.CONFIRMED
    order.reviewed_by = admin.id
    order.reviewed_at = datetime.now(UTC)
    order.admin_message = payload.notes if payload else None

    db.commit()
    db.refresh(order)

    logger.info("order_accepted", order_id=order.id, admin_id=admin.id)
    return _to_read(order)


# ══════════════════════════════════════════════════════════════════════
# Reject — PENDING or CONFIRMED → REJECTED
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/{order_id}/reject",
    response_model=OrderReadAdmin,
    summary="Reject an order with reason",
)
async def reject_order(
    db: DbSession,
    admin: CurrentAdmin,
    order_id: int,
    payload: OrderRejectPayload,
) -> OrderReadAdmin:
    """Reject an order from PENDING or CONFIRMED status."""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found.")
    if order.status not in {OrderStatus.PENDING, OrderStatus.CONFIRMED}:
        raise ConflictError(f"Cannot reject order in status {order.status}.")

    order.status = OrderStatus.REJECTED
    order.reviewed_by = admin.id
    order.reviewed_at = datetime.now(UTC)
    order.admin_message = payload.reason

    db.commit()
    db.refresh(order)

    logger.info(
        "order_rejected",
        order_id=order.id,
        admin_id=admin.id,
        reason=payload.reason,
    )
    return _to_read(order)


# ══════════════════════════════════════════════════════════════════════
# Ship — CONFIRMED → SHIPPED
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/{order_id}/ship",
    response_model=OrderReadAdmin,
    summary="Mark order as shipped",
)
async def ship_order(
    db: DbSession,
    admin: CurrentAdmin,
    order_id: int,
) -> OrderReadAdmin:
    """Mark a confirmed order as SHIPPED."""
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id} not found.")
    if order.status != OrderStatus.CONFIRMED:
        raise ConflictError(f"Cannot ship order in status {order.status}.")

    order.status = OrderStatus.SHIPPED
    order.reviewed_by = admin.id
    order.reviewed_at = datetime.now(UTC)

    db.commit()
    db.refresh(order)

    logger.info("order_shipped", order_id=order.id, admin_id=admin.id)
    return _to_read(order)
