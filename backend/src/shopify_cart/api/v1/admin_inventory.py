"""
Admin inventory endpoints:
  - Alerts (list + resolve)
  - Reorder suggestions
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
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
from shopify_cart.models.analytics import InventoryAlert
from shopify_cart.services.reorder_service import ReorderService

router = APIRouter(prefix="/admin/inventory", tags=["admin:inventory"])


# ----------------------------------------------------------------------
# Schemas (kept local to this module)
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# Alerts
# ----------------------------------------------------------------------
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
    rows, total = paginate_query(db, stmt, params)
    return build_page([InventoryAlertRead.model_validate(r) for r in rows], total, params)


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


# ----------------------------------------------------------------------
# Reorder suggestions
# ----------------------------------------------------------------------
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
