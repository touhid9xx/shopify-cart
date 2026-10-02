"""Cart endpoints — authenticated user only."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from shopify_cart.api.deps import CurrentUser, DbSession
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.schemas.cart import (
    CartItemAdd,
    CartItemProductSnapshot,
    CartItemReadWithProduct,
    CartItemUpdate,
    CartReadWithProducts,
)
from shopify_cart.services.cart_service import CartService

router = APIRouter(prefix="/cart", tags=["cart"])


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


def _to_read(cart) -> CartReadWithProducts:  # type: ignore[no-untyped-def]
    """Build cart response with embedded product snapshots.

    Requires CartService queries to selectinload(CartItem.product).
    """
    items: list[CartItemReadWithProduct] = []
    for i in cart.items:
        if i.product is None:
            continue  # safety: skip if product row was deleted

        items.append(
            CartItemReadWithProduct(
                id=i.id,
                product_id=i.product_id,
                quantity=i.quantity,
                unit_price=i.unit_price,
                subtotal=i.subtotal,
                created_at=i.created_at,
                updated_at=i.updated_at,
                product=CartItemProductSnapshot(
                    id=i.product.id,
                    name=i.product.name,
                    sku=i.product.sku,
                    price=i.product.price,
                    image_url=i.product.image_url,
                    is_active=i.product.is_active,
                ),
            )
        )

    total_qty = sum(i.quantity for i in items)
    total_amount = CartService.total_amount(cart)

    return CartReadWithProducts(
        id=cart.id,
        user_id=cart.user_id,
        items=items,
        item_count=len(items),
        total_quantity=total_qty,
        total_amount=total_amount,
        created_at=cart.created_at,
        updated_at=cart.updated_at,
    )


@router.get("", response_model=CartReadWithProducts, summary="Get current user's cart")
def get_cart(db: DbSession, user: CurrentUser) -> CartReadWithProducts:
    cart = CartService.get_or_create(db, user.id)
    return _to_read(cart)


@router.post(
    "/items",
    response_model=CartReadWithProducts,
    status_code=status.HTTP_200_OK,
    summary="Add an item to cart (idempotent per product)",
)
async def add_item(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
    payload: CartItemAdd,
) -> CartReadWithProducts:
    cart = await CartService.add_item(
        db,
        producer,
        user_id=user.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )
    return _to_read(cart)


@router.patch(
    "/items/{item_id}",
    response_model=CartReadWithProducts,
    summary="Update item quantity (0 removes the item)",
)
async def update_item(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
    item_id: int,
    payload: CartItemUpdate,
) -> CartReadWithProducts:
    cart = await CartService.update_item(
        db,
        producer,
        user_id=user.id,
        item_id=item_id,
        quantity=payload.quantity,
    )
    return _to_read(cart)


@router.delete(
    "/items/{item_id}",
    response_model=CartReadWithProducts,
    summary="Remove an item from cart",
)
async def remove_item(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
    item_id: int,
) -> CartReadWithProducts:
    cart = await CartService.remove_item(
        db,
        producer,
        user_id=user.id,
        item_id=item_id,
    )
    return _to_read(cart)


@router.delete(
    "",
    response_model=CartReadWithProducts,
    summary="Clear the entire cart",
)
async def clear_cart(
    db: DbSession,
    producer: ProducerDep,
    user: CurrentUser,
) -> CartReadWithProducts:
    cart = await CartService.clear(db, producer, user_id=user.id)
    return _to_read(cart)
