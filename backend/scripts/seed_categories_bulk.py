"""
Seed categories (idempotent).

Ensures a canonical set of categories exist before bulk product seeding.
Safe to re-run: skips existing slugs.

Usage:
    python scripts/seed_categories_bulk.py
"""

from __future__ import annotations

from sqlalchemy import select

from shopify_cart.db.session import SessionLocal
from shopify_cart.models.category import Category


# ═══════════════════════════════════════════════════════════════
# Canonical categories — parent_slug=None → root category
# ═══════════════════════════════════════════════════════════════
CATEGORIES: list[tuple[str, str, str | None]] = [
    # (name, slug, parent_slug)
    # ─── Top-level ───
    ("Clothing", "clothing", None),
    ("Footwear", "footwear", None),
    ("Accessories", "accessories", None),
    ("Electronics", "electronics", None),
    ("Home & Kitchen", "home-kitchen", None),
    ("Sports & Outdoors", "sports-outdoors", None),
    ("Beauty", "beauty", None),
    ("Toys & Games", "toys-games", None),
    ("Books", "books", None),
    ("Pet Supplies", "pet-supplies", None),
    # ─── Clothing subcategories ───
    ("Shirts", "shirts", "clothing"),
    ("Trousers", "trousers", "clothing"),
    ("Dresses", "dresses", "clothing"),
    ("Jackets & Coats", "jackets-coats", "clothing"),
    ("Sweaters", "sweaters", "clothing"),
    ("Activewear", "activewear", "clothing"),
    # ─── Footwear subcategories ───
    ("Sneakers", "sneakers", "footwear"),
    ("Boots", "boots", "footwear"),
    ("Sandals", "sandals", "footwear"),
    ("Formal Shoes", "formal-shoes", "footwear"),
    # ─── Accessories subcategories ───
    ("Bags & Backpacks", "bags-backpacks", "accessories"),
    ("Watches", "watches", "accessories"),
    ("Jewelry", "jewelry", "accessories"),
    ("Hats & Caps", "hats-caps", "accessories"),
    # ─── Electronics subcategories ───
    ("Headphones", "headphones", "electronics"),
    ("Smart Home", "smart-home", "electronics"),
    ("Computers", "computers", "electronics"),
    ("Mobile Accessories", "mobile-accessories", "electronics"),
    ("Cameras", "cameras", "electronics"),
    # ─── Sports subcategories ───
    ("Fitness Equipment", "fitness-equipment", "sports-outdoors"),
    ("Outdoor Gear", "outdoor-gear", "sports-outdoors"),
    ("Cycling", "cycling", "sports-outdoors"),
]


def main() -> None:
    db = SessionLocal()
    try:
        # First pass — create roots
        slug_to_id: dict[str, int] = {}

        for name, slug, parent_slug in CATEGORIES:
            existing = db.execute(
                select(Category).where(Category.slug == slug)
            ).scalar_one_or_none()
            if existing is not None:
                slug_to_id[slug] = existing.id
                continue
            # Root categories only in this pass
            if parent_slug is None:
                cat = Category(name=name, slug=slug, parent_id=None)
                db.add(cat)
                db.flush()
                slug_to_id[slug] = cat.id

        db.commit()
        print(f"✅ Roots ensured: {len([s for s in slug_to_id if s])}")

        # Second pass — children (parents now exist)
        for name, slug, parent_slug in CATEGORIES:
            if parent_slug is None:
                continue
            existing = db.execute(
                select(Category).where(Category.slug == slug)
            ).scalar_one_or_none()
            if existing is not None:
                slug_to_id[slug] = existing.id
                continue
            parent_id = slug_to_id.get(parent_slug)
            if parent_id is None:
                print(f"⚠️  Skipping {slug}: parent {parent_slug} missing")
                continue
            cat = Category(name=name, slug=slug, parent_id=parent_id)
            db.add(cat)
            db.flush()
            slug_to_id[slug] = cat.id

        db.commit()
        print(f"✅ Categories seeded: {len(slug_to_id)} total")

    finally:
        db.close()


if __name__ == "__main__":
    main()
