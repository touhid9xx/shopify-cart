"""Inventory endpoints — read (public), adjust (admin)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.schemas.inventory import InventoryAdjust, InventoryRead
from shopify_cart.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])


def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


@router.get(
    "/product/{product_id}",
    response_model=list[InventoryRead],
    summary="List inventory rows for a product",
)
def list_inventory_for_product(db: DbSession, product_id: int) -> list[InventoryRead]:
    rows = InventoryService.list_for_product(db, product_id)
    return [InventoryRead.model_validate(r) for r in rows]


@router.patch(
    "/{inventory_id}/adjust",
    response_model=InventoryRead,
    summary="Adjust inventory quantity (admin only)",
)
async def adjust_inventory(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    inventory_id: int,
    payload: InventoryAdjust,
) -> InventoryRead:
    inv = await InventoryService.adjust(
        db,
        producer,
        inventory_id,
        delta=payload.delta,
        reason=payload.reason,
    )
    return InventoryRead.model_validate(inv)
