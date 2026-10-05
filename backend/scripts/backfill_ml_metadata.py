"""
Backfill ML metadata for bulk-seeded products.

Simulates that the ResNet-18 classifier was run on every bulk product.
- 90% get high confidence (0.80-0.99) → auto-categorized
- 8% get medium confidence (0.75-0.80) → borderline
- 2% get low confidence (0.55-0.75) → would need review

Deterministic (seeded RNG) — same output every run.

Usage:
    python scripts/backfill_ml_metadata.py
    python scripts/backfill_ml_metadata.py --dry-run
"""

from __future__ import annotations

import argparse
import random
from decimal import Decimal

from sqlalchemy import select

from shopify_cart.db.session import SessionLocal
from shopify_cart.models.category import Category
from shopify_cart.models.product import Product


def confidence_for(category_slug: str, rng: random.Random) -> float:
    """
    Assign a plausible confidence based on category 'recognizability'.

    Shirts/sneakers/electronics → high confidence (easy classes).
    Jewelry/hats/beauty → lower confidence (visual overlap).
    """
    # Categories that ML finds harder to distinguish
    hard = {"jewelry", "hats-caps", "beauty", "books", "toys-games"}
    medium = {"shirts", "trousers", "dresses", "headphones"}

    roll = rng.random()

    if category_slug in hard:
        # 60% high, 30% medium, 10% low
        if roll < 0.60:
            return rng.uniform(0.80, 0.95)
        elif roll < 0.90:
            return rng.uniform(0.75, 0.85)
        else:
            return rng.uniform(0.55, 0.75)
    elif category_slug in medium:
        # 85% high, 10% medium, 5% low
        if roll < 0.85:
            return rng.uniform(0.85, 0.99)
        elif roll < 0.95:
            return rng.uniform(0.78, 0.88)
        else:
            return rng.uniform(0.60, 0.78)
    else:
        # Easy categories
        if roll < 0.95:
            return rng.uniform(0.88, 0.99)
        else:
            return rng.uniform(0.72, 0.88)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    db = SessionLocal()
    try:
        # Load categories
        categories = {
            c.id: c.slug
            for c in db.execute(select(Category)).scalars().all()
        }
        print(f"📚 Loaded {len(categories)} categories.")

        # Load products WITHOUT ml metadata (bulk-seeded ones)
        products = list(
            db.execute(
                select(Product).where(Product.ml_category_slug.is_(None))
            ).scalars().all()
        )
        print(f"📦 Found {len(products)} products without ML metadata.")

        if not products:
            print("✅ Nothing to backfill — all products already have ML metadata.")
            return

        updated = 0
        skipped_no_category = 0
        by_confidence: dict[str, int] = {"high": 0, "medium": 0, "low": 0}

        for p in products:
            cat_slug = categories.get(p.category_id or 0)
            if not cat_slug:
                skipped_no_category += 1
                continue

            conf = confidence_for(cat_slug, rng)
            p.ml_category_slug = cat_slug
            p.ml_confidence = Decimal(f"{conf:.4f}")

            if conf >= 0.85:
                by_confidence["high"] += 1
            elif conf >= 0.75:
                by_confidence["medium"] += 1
            else:
                by_confidence["low"] += 1

            updated += 1

        if args.dry_run:
            print(f"\n[DRY RUN] Would update {updated} products.")
            db.rollback()
        else:
            db.commit()
            print(f"\n✅ Updated {updated} products.")

        print(f"   Skipped (no category): {skipped_no_category}")
        print(f"   Confidence distribution:")
        print(f"     High (≥ 0.85):   {by_confidence['high']}")
        print(f"     Medium (0.75-0.85): {by_confidence['medium']}")
        print(f"     Low (< 0.75):    {by_confidence['low']}")

    except Exception as exc:
        db.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
