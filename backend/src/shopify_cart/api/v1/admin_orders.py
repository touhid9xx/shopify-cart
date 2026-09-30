"""Admin order endpoints — list all, change status."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
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
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.models.order import Order, OrderStatus
from shopify_cart.schemas.order import OrderItemRead, OrderRead, OrderStatusUpdate
from shopify_cart.services.order_service import OrderService

router = APIRouter(prefix="/admin/orders", tags=["admin:orders"])


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


def _to_read(order: Order) -> OrderRead:
    items = [OrderItemRead.model_validate(i) for i in order.items]
    return OrderRead(
        id=order.id,
        user_id=order.user_id,
        status=order.status,
        total_amount=order.total_amount,
        shipping_address=order.shipping_address,
        notes=order.notes,
        items=items,
        item_count=len(items),
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.get("", response_model=Page[OrderRead])
def list_all_orders(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> Page[OrderRead]:
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(Order.status == status_filter)

    result: tuple[list[Order], int] = paginate_query(db, stmt, params)
    rows, total = result
    return build_page([_to_read(o) for o in rows], total, params)


@router.patch(
    "/{order_id}/status",
    response_model=OrderRead,
    summary="Change order status (admin only)",
)
async def change_status(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    order_id: int,
    payload: OrderStatusUpdate,
) -> OrderRead:
    order = await OrderService.change_status(
        db,
        producer,
        order_id=order_id,
        new_status=payload.status,
        reason=payload.reason,
    )
    return _to_read(order)
