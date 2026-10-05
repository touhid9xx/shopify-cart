"""
ML Insights service.

Three responsibilities:
  1. summarize()        — model + review KPIs, confidence histogram, category dist
  2. demand_forecast()  — exponential smoothing per product
  3. detect_anomalies() — rolling z-score over sales history
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from shopify_cart.logging_config import get_logger
from shopify_cart.models.analytics import DailySales
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product, ProductReviewStatus
from shopify_cart.schemas.ml_insights import (
    AnomalyItem,
    CategoryCount,
    ConfidenceBucket,
    DemandForecastItem,
    MLSummaryResponse,
)

logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Tunable constants
# ══════════════════════════════════════════════════════════════════════
EXP_SMOOTHING_ALPHA = 0.3  # 0..1 — higher = more weight on recent days
ANOMALY_Z_THRESHOLD = 2.0  # |z| above this is an anomaly
ANOMALY_WINDOW = 7  # rolling window (days)
LOW_STOCK_LOOKBACK = 7  # days to consider "recent" for stockout
CATEGORY_TOP_N = 10  # top categories in summary
EPSILON = 1e-6


class MLInsightsService:
    # ══════════════════════════════════════════════════════════════
    # 1. Summary
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def summarize(db: Session) -> MLSummaryResponse:
        """Aggregate model health + review outcomes."""

        # ── Total counts ──
        total_products = db.execute(select(func.count(Product.id))).scalar_one()

        products_with_ml = db.execute(
            select(func.count(Product.id)).where(Product.ml_category_slug.is_not(None))
        ).scalar_one()

        products_without_ml = total_products - products_with_ml

        # ── Confidence stats ──
        avg_conf_row = db.execute(
            select(func.avg(Product.ml_confidence)).where(Product.ml_confidence.is_not(None))
        ).scalar_one()
        avg_confidence = float(avg_conf_row) if avg_conf_row is not None else 0.0

        # Confidence tier counts
        high_count = db.execute(
            select(func.count(Product.id)).where(Product.ml_confidence >= Decimal("0.85"))
        ).scalar_one()

        medium_count = db.execute(
            select(func.count(Product.id)).where(
                Product.ml_confidence >= Decimal("0.75"),
                Product.ml_confidence < Decimal("0.85"),
            )
        ).scalar_one()

        low_count = db.execute(
            select(func.count(Product.id)).where(Product.ml_confidence < Decimal("0.75"))
        ).scalar_one()

        # ── Review workflow ──
        pending_count = db.execute(
            select(func.count(Product.id)).where(
                Product.review_status == ProductReviewStatus.PENDING
            )
        ).scalar_one()

        approved_count = db.execute(
            select(func.count(Product.id)).where(
                Product.review_status == ProductReviewStatus.APPROVED
            )
        ).scalar_one()

        rejected_count = db.execute(
            select(func.count(Product.id)).where(
                Product.review_status == ProductReviewStatus.REJECTED
            )
        ).scalar_one()

        decided = approved_count + rejected_count
        approval_rate = (approved_count / decided) if decided > 0 else 0.0

        # ── Confidence histogram (fixed buckets) ──
        buckets_def = [
            (0.50, 0.60, "0.50-0.60"),
            (0.60, 0.70, "0.60-0.70"),
            (0.70, 0.75, "0.70-0.75"),
            (0.75, 0.85, "0.75-0.85"),
            (0.85, 0.95, "0.85-0.95"),
            (0.95, 1.01, "0.95-1.00"),
        ]
        confidence_buckets: list[ConfidenceBucket] = []
        for lo, hi, label in buckets_def:
            count = db.execute(
                select(func.count(Product.id)).where(
                    Product.ml_confidence >= Decimal(str(lo)),
                    Product.ml_confidence < Decimal(str(hi)),
                )
            ).scalar_one()
            confidence_buckets.append(
                ConfidenceBucket(
                    range_label=label,
                    range_min=lo,
                    range_max=min(hi, 1.0),
                    count=count,
                )
            )

        # ── Category distribution ──
        cat_rows = db.execute(
            select(
                Product.ml_category_slug,
                func.count(Product.id).label("cnt"),
                func.avg(Product.ml_confidence).label("avg_conf"),
            )
            .where(Product.ml_category_slug.is_not(None))
            .group_by(Product.ml_category_slug)
            .order_by(func.count(Product.id).desc())
            .limit(CATEGORY_TOP_N)
        ).all()

        category_distribution = [
            CategoryCount(
                category_slug=slug,
                product_count=int(cnt),
                avg_confidence=float(avg_c) if avg_c else 0.0,
            )
            for slug, cnt, avg_c in cat_rows
            if slug is not None
        ]

        return MLSummaryResponse(
            total_products=total_products,
            products_with_ml=products_with_ml,
            products_without_ml=products_without_ml,
            avg_confidence=round(avg_confidence, 4),
            high_confidence_count=high_count,
            medium_confidence_count=medium_count,
            low_confidence_count=low_count,
            pending_review_count=pending_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            approval_rate=round(approval_rate, 4),
            confidence_buckets=confidence_buckets,
            category_distribution=category_distribution,
        )

    # ══════════════════════════════════════════════════════════════
    # 2. Demand Forecast (exponential smoothing)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def _exponential_smooth(quantities: list[int], alpha: float) -> float:
        """
        Simple exponential smoothing.

        s_0 = x_0
        s_t = alpha * x_t + (1 - alpha) * s_{t-1}

        Returns the final smoothed level (used as next-day forecast).
        """
        if not quantities:
            return 0.0
        s = float(quantities[0])
        for x in quantities[1:]:
            s = alpha * float(x) + (1 - alpha) * s
        return s

    @staticmethod
    def _trend_from_halves(quantities: list[int]) -> str:
        """Classify trend by comparing first half vs second half mean."""
        if len(quantities) < 4:
            return "stable"
        mid = len(quantities) // 2
        first = statistics.mean(quantities[:mid])
        second = statistics.mean(quantities[mid:])
        if second > first * 1.15:
            return "increasing"
        if second < first * 0.85:
            return "decreasing"
        return "stable"

    @staticmethod
    def demand_forecast(
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        lookback_days: int = 30,
        only_low_stock: bool = False,
    ) -> tuple[list[DemandForecastItem], int]:
        """
        Compute demand forecast for products.

        Returns (items, total). Items are sorted by `days_of_stock` ascending
        — most urgent first.
        """
        since = date.today() - timedelta(days=lookback_days - 1)

        # Fetch sales for window
        sales_rows = db.execute(
            select(
                DailySales.product_id,
                DailySales.sales_date,
                DailySales.quantity,
            )
            .where(DailySales.sales_date >= since)
            .order_by(DailySales.product_id, DailySales.sales_date)
        ).all()

        # Group sales by product
        sales_by_product: dict[int, dict[date, int]] = defaultdict(dict)
        for pid, sale_date, qty in sales_rows:
            sales_by_product[pid][sale_date] = qty

        # Fetch inventory — skip products with no inventory
        inv_rows = db.execute(
            select(Inventory, Product).join(Product, Product.id == Inventory.product_id)
        ).all()

        # Aggregate inventory per product (sum across locations)
        inv_by_product: dict[int, dict[str, Any]] = defaultdict(
            lambda: {"qty": 0, "threshold": 0, "product": None}
        )
        for inv, product_row in inv_rows:
            entry = inv_by_product[product_row.id]
            entry["qty"] += inv.quantity
            # Use max threshold across locations (most conservative)
            entry["threshold"] = max(entry["threshold"], inv.low_stock_threshold)
            entry["product"] = product_row

        # Build forecast rows
        forecasts: list[DemandForecastItem] = []

        for pid, entry in inv_by_product.items():
            product: Product = entry["product"]
            current_qty = entry["qty"]
            threshold = entry["threshold"]

            # Optional low-stock filter
            if only_low_stock and current_qty > threshold:
                continue

            product_sales = sales_by_product.get(pid, {})

            # Build dense daily series (fill missing days with 0)
            series: list[int] = []
            for i in range(lookback_days):
                d = since + timedelta(days=i)
                series.append(product_sales.get(d, 0))

            # Smooth + trend
            smoothed_avg = MLInsightsService._exponential_smooth(series, EXP_SMOOTHING_ALPHA)
            trend = MLInsightsService._trend_from_halves(series)

            # 7d/30d forecast = smoothed daily x days
            forecast_7d = math.ceil(smoothed_avg * 7)
            forecast_30d = math.ceil(smoothed_avg * 30)

            # Days of stock remaining
            days_of_stock = round(current_qty / smoothed_avg, 1) if smoothed_avg > EPSILON else None

            # Recent actuals
            units_7d = sum(series[-7:])
            units_30d = sum(series)

            will_stockout_7d = days_of_stock is not None and days_of_stock < 7

            forecasts.append(
                DemandForecastItem(
                    product_id=pid,
                    sku=product.sku,
                    name=product.name,
                    image_url=product.image_url,
                    current_quantity=current_qty,
                    low_stock_threshold=threshold,
                    avg_daily_demand=round(smoothed_avg, 3),
                    forecast_7d=forecast_7d,
                    forecast_30d=forecast_30d,
                    days_of_stock=days_of_stock,
                    will_stockout_7d=will_stockout_7d,
                    trend=trend,  # type: ignore[arg-type]
                    units_sold_7d=units_7d,
                    units_sold_30d=units_30d,
                )
            )

        # Sort by urgency: stockout first, then days_of_stock ascending
        forecasts.sort(
            key=lambda f: (
                not f.will_stockout_7d,
                f.days_of_stock if f.days_of_stock is not None else 999_999,
            )
        )

        total = len(forecasts)
        start = (page - 1) * size
        end = start + size
        return forecasts[start:end], total

    # ══════════════════════════════════════════════════════════════
    # 3. Anomaly Detection (rolling z-score)
    # ══════════════════════════════════════════════════════════════
    @staticmethod
    def detect_anomalies(
        db: Session,
        *,
        page: int = 1,
        size: int = 20,
        lookback_days: int = 30,
        z_threshold: float = ANOMALY_Z_THRESHOLD,
    ) -> tuple[list[AnomalyItem], int]:
        """
        Detect sales anomalies using rolling z-score.

        For each product-day:
          window = previous ANOMALY_WINDOW days of quantities
          mean   = mean(window)
          std    = std(window)
          z      = (qty - mean) / (std + eps)

        Flag if |z| > threshold.

        Sorted by |z_score| descending — most unusual first.
        """
        since = date.today() - timedelta(days=lookback_days - 1)

        # Fetch all sales in window + rolling context (need extra days for window)
        context_since = since - timedelta(days=ANOMALY_WINDOW)

        rows = db.execute(
            select(
                DailySales.product_id,
                DailySales.sales_date,
                DailySales.quantity,
            )
            .where(DailySales.sales_date >= context_since)
            .order_by(DailySales.product_id, DailySales.sales_date)
        ).all()

        # Group by product -> list of (date, qty)
        by_product: dict[int, list[tuple[date, int]]] = defaultdict(list)
        for pid, sale_date, qty in rows:
            by_product[pid].append((sale_date, qty))

        # Product lookup
        product_map = {p.id: p for p in db.execute(select(Product)).scalars().all()}

        anomalies: list[AnomalyItem] = []

        for pid, series in by_product.items():
            if len(series) < ANOMALY_WINDOW + 1:
                continue

            product = product_map.get(pid)
            if product is None:
                continue

            for i in range(ANOMALY_WINDOW, len(series)):
                sale_date, qty = series[i]

                # Skip days before lookback start
                if sale_date < since:
                    continue

                window = [q for _, q in series[i - ANOMALY_WINDOW : i]]
                mean = statistics.mean(window)
                std = statistics.pstdev(window) if len(window) > 1 else 0.0

                z = (qty - mean) / (std + EPSILON)

                if abs(z) < z_threshold:
                    continue

                direction = "spike" if z > 0 else "drop"
                abs_z = abs(z)
                if abs_z >= 3.0:
                    severity = "high"
                elif abs_z >= 2.5:
                    severity = "medium"
                else:
                    severity = "low"

                anomalies.append(
                    AnomalyItem(
                        sales_date=sale_date,
                        product_id=pid,
                        sku=product.sku,
                        name=product.name,
                        image_url=product.image_url,
                        quantity=qty,
                        expected_quantity=round(mean, 2),
                        rolling_std=round(std, 2),
                        z_score=round(z, 2),
                        direction=direction,  # type: ignore[arg-type]
                        severity=severity,  # type: ignore[arg-type]
                    )
                )

        # Sort by |z| desc (most severe first)
        anomalies.sort(key=lambda a: abs(a.z_score), reverse=True)

        total = len(anomalies)
        start = (page - 1) * size
        end = start + size
        return anomalies[start:end], total
