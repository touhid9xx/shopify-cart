"""Admin analytics — daily sales, low-stock alerts, resolution."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
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
from shopify_cart.models.analytics import DailySales, InventoryAlert

router = APIRouter(prefix="/admin/analytics", tags=["admin:analytics"])


class DailySalesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sales_date: date
    product_id: int
    quantity: int
    revenue: Decimal
    order_count: int


class InventoryAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    location: str
    quantity: int
    threshold: int
    resolved_at: datetime | None
    created_at: datetime


@router.get("/sales", response_model=Page[DailySalesRead])
def list_daily_sales(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
    day: Annotated[date | None, Query(description="Filter by date (YYYY-MM-DD)")] = None,
) -> Page[DailySalesRead]:
    stmt = select(DailySales).order_by(DailySales.sales_date.desc(), DailySales.id.desc())
    if day is not None:
        stmt = stmt.where(DailySales.sales_date == day)
    rows: list[DailySales]
    rows, total = paginate_query(db, stmt, params)
    return build_page([DailySalesRead.model_validate(r) for r in rows], total, params)


@router.get("/alerts", response_model=Page[InventoryAlertRead])
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


@router.post("/alerts/{alert_id}/resolve", response_model=InventoryAlertRead)
def resolve_alert(
    db: DbSession,
    _admin: CurrentAdmin,
    alert_id: int,
) -> InventoryAlertRead:
    alert = db.get(InventoryAlert, alert_id)
    if alert is None:
        raise NotFoundError(f"Alert {alert_id} not found.")
    if alert.resolved_at is None:
        from datetime import UTC

        alert.resolved_at = datetime.now(UTC)
        db.commit()
        db.refresh(alert)
    return InventoryAlertRead.model_validate(alert)
