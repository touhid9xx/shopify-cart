"""User-facing order endpoints — checkout, history, detail, cancel."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from shopify_cart.api.deps import CurrentUser, DbSession
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.schemas.order import (
    CheckoutRequest,
    OrderCancelRequest,
    OrderItemRead,
    OrderRead,
)
from shopify_cart.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


def _to_read(order) -> OrderRead:  # type: ignore[no-untyped-def]
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


@router.post(
    "/checkout",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Convert the current cart into an order (atomic)",
)
async def checkout(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
    payload: CheckoutRequest,
) -> OrderRead:
    order = await OrderService.checkout(
        db,
        producer,
        user_id=user.id,
        shipping_address=payload.shipping_address,
        notes=payload.notes,
    )
    return _to_read(order)


@router.get(
    "",
    response_model=list[OrderRead],
    summary="List the current user's orders (newest first)",
)
def list_orders(db: DbSession, user: CurrentUser) -> list[OrderRead]:
    orders = OrderService.list_for_user(db, user.id)
    return [_to_read(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderRead,
    summary="Get order detail",
)
def get_order(db: DbSession, user: CurrentUser, order_id: int) -> OrderRead:
    order = OrderService.get_by_id(db, order_id)
    if order.user_id != user.id and not user.is_admin:
        # Pretend not found
        from shopify_cart.exceptions import NotFoundError

        raise NotFoundError(f"Order {order_id} not found.")
    return _to_read(order)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderRead,
    summary="Cancel an order (restores inventory)",
)
async def cancel_order(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
    order_id: int,
    payload: OrderCancelRequest,
) -> OrderRead:
    order = await OrderService.cancel(
        db,
        producer,
        order_id=order_id,
        acting_user_id=user.id,
        is_admin=user.is_admin,
        reason=payload.reason,
    )
    return _to_read(order)
