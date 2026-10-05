"""
Admin inventory endpoints:
  - List (paginated, filterable)
  - Stats (KPIs)
  - Adjust (delta-based)
  - Per-product lookup
  - Alerts (list + resolve)
  - Reorder suggestions
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.core.pagination import (
    Page,
    PageParams,
    build_page,
    get_page_params,
    paginate_query,
)
from shopify_cart.exceptions import NotFoundError
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.models.analytics import InventoryAlert
from shopify_cart.models.product import Product
from shopify_cart.schemas.inventory import (
    InventoryStats,
    InventoryWithProduct,
    ProductSnapshot,
)
from shopify_cart.services.inventory_service import InventoryService
from shopify_cart.services.reorder_service import ReorderService

router = APIRouter(prefix="/admin/inventory", tags=["admin:inventory"])


# ══════════════════════════════════════════════════════════════════════
# Dependency helpers
# ══════════════════════════════════════════════════════════════════════
def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


# ══════════════════════════════════════════════════════════════════════
# Local schemas
# ══════════════════════════════════════════════════════════════════════
class InventoryAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    location: str
    quantity: int
    threshold: int
    resolved_at: datetime | None
    created_at: datetime


class ReorderSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    sku: str
    name: str
    location: str
    current_quantity: int
    low_stock_threshold: int
    avg_daily_demand: float
    lookback_days: int
    lead_time_days: int
    safety_multiplier: float
    target_stock: int
    suggested_reorder_qty: int
    reason: str


class ReorderListResponse(BaseModel):
    items: list[ReorderSuggestionRead] = Field(default_factory=list)
    total: int


class AdjustRequest(BaseModel):
    """Body for POST /admin/inventory/adjust."""

    product_id: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=80)
    delta: int = Field(description="Positive to add, negative to remove.")
    reason: str | None = Field(default=None, max_length=255)


# ══════════════════════════════════════════════════════════════════════
# List + stats
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "",
    response_model=Page[InventoryWithProduct],
    summary="List inventory rows (paginated, filterable)",
)
def list_inventory(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
    low_stock_only: Annotated[bool, Query()] = False,
    out_of_stock_only: Annotated[bool, Query()] = False,
    search: Annotated[str | None, Query(max_length=120)] = None,
    location: Annotated[str | None, Query(max_length=80)] = None,
) -> Page[InventoryWithProduct]:
    rows, total = InventoryService.list_all(
        db,
        low_stock_only=low_stock_only,
        out_of_stock_only=out_of_stock_only,
        search=search,
        location=location,
        offset=params.offset,
        limit=params.size,
    )

    # Load all referenced products in a single query — avoids N+1.
    product_ids = {r.product_id for r in rows}
    product_map: dict[int, Product] = {}
    if product_ids:
        for p in db.execute(select(Product).where(Product.id.in_(product_ids))).scalars():
            product_map[p.id] = p

    items = [
        InventoryWithProduct(
            id=r.id,
            product_id=r.product_id,
            location=r.location,
            quantity=r.quantity,
            low_stock_threshold=r.low_stock_threshold,
            is_low_stock=r.is_low_stock,
            created_at=r.created_at,
            updated_at=r.updated_at,
            product=ProductSnapshot(
                id=product_map[r.product_id].id,
                sku=product_map[r.product_id].sku,
                name=product_map[r.product_id].name,
                image_url=product_map[r.product_id].image_url,
                price=product_map[r.product_id].price,
                is_active=product_map[r.product_id].is_active,
                review_status=str(product_map[r.product_id].review_status.value),
            ),
        )
        for r in rows
    ]
    return build_page(items, total, params)


@router.get(
    "/stats",
    response_model=InventoryStats,
    summary="Aggregated inventory KPIs",
)
def inventory_stats(
    db: DbSession,
    _admin: CurrentAdmin,
) -> InventoryStats:
    data = InventoryService.stats(db)
    return InventoryStats(
        total_skus=int(data["total_skus"]),
        total_units=int(data["total_units"]),
        low_stock_count=int(data["low_stock_count"]),
        out_of_stock_count=int(data["out_of_stock_count"]),
        total_inventory_value=cast(Decimal, data["total_inventory_value"]),
    )


# ══════════════════════════════════════════════════════════════════════
# Per-product inventory
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "/product/{product_id}",
    response_model=list[InventoryWithProduct],
    summary="All inventory rows for one product (multi-location)",
)
def inventory_for_product(
    db: DbSession,
    _admin: CurrentAdmin,
    product_id: int,
) -> list[InventoryWithProduct]:
    rows = InventoryService.list_for_product(db, product_id)
    if not rows:
        return []

    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found.")

    return [
        InventoryWithProduct(
            id=r.id,
            product_id=r.product_id,
            location=r.location,
            quantity=r.quantity,
            low_stock_threshold=r.low_stock_threshold,
            is_low_stock=r.is_low_stock,
            created_at=r.created_at,
            updated_at=r.updated_at,
            product=ProductSnapshot(
                id=product.id,
                sku=product.sku,
                name=product.name,
                image_url=product.image_url,
                price=product.price,
                is_active=product.is_active,
                review_status=str(product.review_status.value),
            ),
        )
        for r in rows
    ]


# ══════════════════════════════════════════════════════════════════════
# Adjust
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/adjust",
    response_model=InventoryWithProduct,
    status_code=status.HTTP_200_OK,
    summary="Adjust stock by delta (positive to add, negative to remove)",
)
async def adjust_inventory(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    payload: AdjustRequest,
) -> InventoryWithProduct:
    inv = await InventoryService.adjust_by_product_location(
        db,
        producer,
        product_id=payload.product_id,
        location=payload.location,
        delta=payload.delta,
        reason=payload.reason,
    )

    product = db.get(Product, inv.product_id)
    assert product is not None  # adjust_by_product_location guarantees

    return InventoryWithProduct(
        id=inv.id,
        product_id=inv.product_id,
        location=inv.location,
        quantity=inv.quantity,
        low_stock_threshold=inv.low_stock_threshold,
        is_low_stock=inv.is_low_stock,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        product=ProductSnapshot(
            id=product.id,
            sku=product.sku,
            name=product.name,
            image_url=product.image_url,
            price=product.price,
            is_active=product.is_active,
            review_status=str(product.review_status.value),
        ),
    )


# ══════════════════════════════════════════════════════════════════════
# Alerts
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "/alerts",
    response_model=Page[InventoryAlertRead],
    summary="List inventory alerts (unresolved by default)",
)
def list_alerts(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
    unresolved_only: Annotated[bool, Query()] = True,
) -> Page[InventoryAlertRead]:
    stmt = select(InventoryAlert).order_by(InventoryAlert.created_at.desc())
    if unresolved_only:
        stmt = stmt.where(InventoryAlert.resolved_at.is_(None))

    rows: list[InventoryAlert]
    total: int
    rows, total = paginate_query(db, stmt, params)
    return build_page(
        [InventoryAlertRead.model_validate(r) for r in rows],
        total,
        params,
    )


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=InventoryAlertRead,
    summary="Mark an alert as resolved (idempotent)",
)
def resolve_alert(
    db: DbSession,
    _admin: CurrentAdmin,
    alert_id: int,
) -> InventoryAlertRead:
    alert = db.get(InventoryAlert, alert_id)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} not found.")

    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(UTC)
        db.commit()
        db.refresh(alert)
    return InventoryAlertRead.model_validate(alert)


# ══════════════════════════════════════════════════════════════════════
# Reorder suggestions
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "/reorder-suggestions",
    response_model=ReorderListResponse,
    summary="ML-based reorder quantity suggestions (moving average)",
)
def reorder_suggestions(
    db: DbSession,
    _admin: CurrentAdmin,
    low_stock_only: Annotated[bool, Query()] = True,
    lookback_days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> ReorderListResponse:
    suggestions = ReorderService.suggest_all(
        db,
        low_stock_only=low_stock_only,
        lookback_days=lookback_days,
        limit=limit,
    )
    return ReorderListResponse(
        items=[ReorderSuggestionRead.model_validate(s) for s in suggestions],
        total=len(suggestions),
    )
