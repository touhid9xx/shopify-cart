"""
Seed daily_sales — 30 days of realistic sales.

Sparse: ~15-20% of (product × day) combinations have a sale.
Zipf-like: top 20% of products account for ~80% of revenue.
Weekend boost: +50% on Sat/Sun.

Idempotent — deletes ALL existing daily_sales rows first.

Usage:
    python scripts/seed_daily_sales_bulk.py
    python scripts/seed_daily_sales_bulk.py --days 45
"""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete, select

from shopify_cart.db.session import SessionLocal
from shopify_cart.models.analytics import DailySales
from shopify_cart.models.product import Product


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    db = SessionLocal()
    try:
        # ─── Clear existing ───
        existing = db.execute(select(DailySales.id).limit(1)).scalar_one_or_none()
        if existing is not None:
            print("🧹 Clearing existing daily_sales rows…")
            db.execute(delete(DailySales))
            db.commit()

        # ─── Load products ───
        products = list(
            db.execute(
                select(Product).where(Product.is_active.is_(True))
            ).scalars().all()
        )
        print(f"📦 Loaded {len(products)} active products.")

        if not products:
            print("⚠️  No products found — run seed_products_bulk.py first.")
            return

        # ─── Zipf-like hotness: top 20% get 80% weight ───
        # Sort products by id for determinism
        products.sort(key=lambda p: p.id)
        n = len(products)
        hot_cutoff = max(1, n // 5)  # top 20%

        hot = products[:hot_cutoff]
        warm = products[hot_cutoff: hot_cutoff * 3]
        cold = products[hot_cutoff * 3:]

        print(
            f"🔥 Hot: {len(hot)} | Warm: {len(warm)} | Cold: {len(cold)}"
        )

        def sale_probability(p: Product) -> float:
            """Daily probability a product sells."""
            if p in hot:
                return 0.75
            if p in warm:
                return 0.40
            return 0.15

        def units_for(p: Product) -> int:
            """Units sold when a sale occurs."""
            if p in hot:
                return rng.randint(1, 6)
            if p in warm:
                return rng.randint(1, 3)
            return rng.randint(1, 2)

        # ─── Generate ───
        today = date.today()
        start = today - timedelta(days=args.days - 1)

        rows: list[DailySales] = []
        batch_size = 500

        for day_offset in range(args.days):
            d = start + timedelta(days=day_offset)
            is_weekend = d.weekday() >= 5

            for p in products:
                prob = sale_probability(p)
                if is_weekend:
                    prob = min(1.0, prob * 1.3)

                if rng.random() > prob:
                    continue  # no sale this product-day

                qty = units_for(p)
                if is_weekend:
                    qty = int(qty * 1.5) or 1

                revenue = (Decimal(p.price) * qty).quantize(Decimal("0.01"))
                order_count = max(1, (qty + 1) // 2)

                rows.append(
                    DailySales(
                        sales_date=d,
                        product_id=p.id,
                        quantity=qty,
                        revenue=revenue,
                        order_count=order_count,
                    )
                )

                if len(rows) >= batch_size:
                    db.add_all(rows)
                    db.commit()
                    rows.clear()

        # Final flush
        if rows:
            db.add_all(rows)
            db.commit()

        # ─── Summary ───
        all_rows = db.execute(select(DailySales)).scalars().all()
        total_units = sum(r.quantity for r in all_rows)
        total_revenue = sum(Decimal(r.revenue) for r in all_rows)

        print("\n" + "═" * 60)
        print(f"✅ Seeded {len(all_rows)} daily_sales rows")
        print(f"   Days:    {args.days}")
        print(f"   Units:   {total_units:,}")
        print(f"   Revenue: ${total_revenue:,.2f}")
        print("═" * 60)

    except Exception as exc:
        db.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
