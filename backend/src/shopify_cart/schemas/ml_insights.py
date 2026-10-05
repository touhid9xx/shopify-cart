"""Pydantic v2 schemas for ML insights (summary, forecast, anomalies)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


# ══════════════════════════════════════════════════════════════════════
# Insights Summary
# ══════════════════════════════════════════════════════════════════════
class CategoryCount(BaseModel):
    """Category distribution — one row per ML-predicted category."""

    category_slug: str
    product_count: int
    avg_confidence: float


class ConfidenceBucket(BaseModel):
    """Histogram bucket for confidence distribution."""

    range_label: str  # e.g. "0.85-0.95"
    range_min: float
    range_max: float
    count: int


class MLSummaryResponse(BaseModel):
    """Aggregated ML model health + review outcome KPIs."""

    total_products: int
    products_with_ml: int
    products_without_ml: int

    avg_confidence: float = Field(ge=0, le=1)
    high_confidence_count: int = Field(description="ml_confidence >= 0.85")
    medium_confidence_count: int = Field(description="0.75 <= conf < 0.85")
    low_confidence_count: int = Field(description="conf < 0.75")

    # Review workflow
    pending_review_count: int
    approved_count: int
    rejected_count: int
    approval_rate: float = Field(ge=0, le=1, description="approved / (approved + rejected)")

    # Distributions
    confidence_buckets: list[ConfidenceBucket]
    category_distribution: list[CategoryCount] = Field(
        description="Top categories by product count"
    )


# ══════════════════════════════════════════════════════════════════════
# Demand Forecast
# ══════════════════════════════════════════════════════════════════════
ForecastTrend = Literal["increasing", "stable", "decreasing"]


class DemandForecastItem(BaseModel):
    """Predicted demand for one product."""

    product_id: int
    sku: str
    name: str
    image_url: str | None = None
    current_quantity: int
    low_stock_threshold: int

    # Demand metrics
    avg_daily_demand: float = Field(description="Exponential-smoothed daily avg")
    forecast_7d: int = Field(description="Predicted units needed next 7 days")
    forecast_30d: int = Field(description="Predicted units needed next 30 days")

    # Derived health
    days_of_stock: float | None = Field(
        default=None,
        description="current_quantity / avg_daily_demand (None if demand is 0)",
    )
    will_stockout_7d: bool
    trend: ForecastTrend

    # Historical reference
    units_sold_7d: int
    units_sold_30d: int


# ══════════════════════════════════════════════════════════════════════
# Anomaly Detection
# ══════════════════════════════════════════════════════════════════════
AnomalyDirection = Literal["spike", "drop"]
AnomalySeverity = Literal["high", "medium", "low"]


class AnomalyItem(BaseModel):
    """One detected sales anomaly."""

    sales_date: date
    product_id: int
    sku: str
    name: str
    image_url: str | None = None

    quantity: int
    expected_quantity: float = Field(description="Rolling mean baseline")
    rolling_std: float
    z_score: float

    direction: AnomalyDirection
    severity: AnomalySeverity


# ══════════════════════════════════════════════════════════════════════
# Pagination wrappers (matches existing convention)
# ══════════════════════════════════════════════════════════════════════
class PaginatedDemandForecast(BaseModel):
    items: list[DemandForecastItem]
    total: int
    page: int
    size: int
    pages: int


class PaginatedAnomalies(BaseModel):
    items: list[AnomalyItem]
    total: int
    page: int
    size: int
    pages: int
