"""
Admin ML insights endpoints:
  - GET /admin/ml/summary
  - GET /admin/ml/demand-forecast
  - GET /admin/ml/anomalies
"""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Query

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.schemas.ml_insights import (
    MLSummaryResponse,
    PaginatedAnomalies,
    PaginatedDemandForecast,
)
from shopify_cart.services.ml_insights_service import MLInsightsService

router = APIRouter(prefix="/admin/ml", tags=["admin:ml-insights"])


@router.get(
    "/summary",
    response_model=MLSummaryResponse,
    summary="ML model + review workflow KPIs",
)
def ml_summary(
    db: DbSession,
    _admin: CurrentAdmin,
) -> MLSummaryResponse:
    """Aggregate health metrics: predictions, confidence, review outcomes."""
    return MLInsightsService.summarize(db)


@router.get(
    "/demand-forecast",
    response_model=PaginatedDemandForecast,
    summary="Per-product demand forecast (exponential smoothing)",
)
def demand_forecast(
    db: DbSession,
    _admin: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    lookback_days: Annotated[int, Query(ge=7, le=180)] = 30,
    only_low_stock: Annotated[bool, Query()] = False,
) -> PaginatedDemandForecast:
    """
    Compute 7d/30d demand forecasts using exponential smoothing.

    Sorted by urgency (soonest stockout first).
    """
    items, total = MLInsightsService.demand_forecast(
        db,
        page=page,
        size=size,
        lookback_days=lookback_days,
        only_low_stock=only_low_stock,
    )
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedDemandForecast(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.get(
    "/anomalies",
    response_model=PaginatedAnomalies,
    summary="Detected sales anomalies (rolling z-score)",
)
def anomalies(
    db: DbSession,
    _admin: CurrentAdmin,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    lookback_days: Annotated[int, Query(ge=7, le=180)] = 30,
    z_threshold: Annotated[float, Query(ge=1.0, le=5.0)] = 2.0,
) -> PaginatedAnomalies:
    """
    Detect sales spikes/drops vs rolling 7-day baseline.

    Sorted by |z-score| descending.
    """
    items, total = MLInsightsService.detect_anomalies(
        db,
        page=page,
        size=size,
        lookback_days=lookback_days,
        z_threshold=z_threshold,
    )
    pages = math.ceil(total / size) if size > 0 else 0
    return PaginatedAnomalies(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
    )
