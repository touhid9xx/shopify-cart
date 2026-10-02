# backend/scripts/seed_categories.py

"""Seed default product categories.

Idempotent — running twice does not duplicate rows.

Usage (PowerShell):
    python scripts\\seed_categories.py
"""

from __future__ import annotations

from sqlalchemy import select

from shopify_cart.config import get_settings
from shopify_cart.db.session import SessionLocal
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.models.category import Category

logger = get_logger(__name__)


# Root categories (parent_slug=None) and their children
SEED: list[dict[str, str | None]] = [
    # ---------- Roots ----------
    {"name": "Clothing", "slug": "clothing", "parent_slug": None},
    {"name": "Footwear", "slug": "footwear", "parent_slug": None},
    {"name": "Accessories", "slug": "accessories", "parent_slug": None},
    # ---------- Clothing ----------
    {"name": "Shirt", "slug": "shirt", "parent_slug": "clothing"},
    {"name": "Trouser", "slug": "trouser", "parent_slug": "clothing"},
    {"name": "Dress", "slug": "dress", "parent_slug": "clothing"},
    {"name": "Jacket", "slug": "jacket", "parent_slug": "clothing"},
    {"name": "Sweater", "slug": "sweater", "parent_slug": "clothing"},
    # ---------- Footwear ----------
    {"name": "Shoe", "slug": "shoe", "parent_slug": "footwear"},
    {"name": "Sandal", "slug": "sandal", "parent_slug": "footwear"},
    {"name": "Boot", "slug": "boot", "parent_slug": "footwear"},
    # ---------- Accessories ----------
    {"name": "Bag", "slug": "bag", "parent_slug": "accessories"},
    {"name": "Hat", "slug": "hat", "parent_slug": "accessories"},
    {"name": "Belt", "slug": "belt", "parent_slug": "accessories"},
]


def main() -> None:
    settings = get_settings()
    configure_logging(
        debug=settings.app_debug,
        json_logs=settings.is_production,
    )

    with SessionLocal() as db:
        # ── First pass: create all rows that don't exist ──
        slug_to_category: dict[str, Category] = {}

        for entry in SEED:
            slug = entry["slug"]
            name = entry["name"]
            if slug is None or name is None:
                # Defensive: types allow None but our seed data never uses it.
                raise ValueError(f"Seed entry missing slug or name: {entry}")

            existing = db.execute(
                select(Category).where(Category.slug == slug)
            ).scalar_one_or_none()
            if existing is not None:
                slug_to_category[slug] = existing
                continue

            cat = Category(
                name=name,
                slug=slug,
                parent_id=None,  # wired in second pass
            )
            db.add(cat)
            db.flush()  # assigns id
            slug_to_category[slug] = cat

        # ── Second pass: wire parents ──
        for entry in SEED:
            parent_slug = entry["parent_slug"]
            if parent_slug is None:
                continue
            slug = entry["slug"]
            if slug is None:
                continue
            child = slug_to_category[slug]
            parent = slug_to_category[parent_slug]
            if child.parent_id != parent.id:
                child.parent_id = parent.id

        db.commit()

    logger.info("seed_categories_done", total=len(SEED))


if __name__ == "__main__":
    main()
