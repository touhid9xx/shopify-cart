"""
Bulk-seed 1000 products + inventories.

Deterministic (seeded RNG) — same output every run.
Idempotent — deletes existing BULK- products before re-creating.

Usage:
    python scripts/seed_products_bulk.py
    python scripts/seed_products_bulk.py --count 500   # override
"""

from __future__ import annotations

import argparse
import random
from decimal import Decimal

from sqlalchemy import delete, select

from shopify_cart.db.session import SessionLocal
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product, ProductReviewStatus


# ═══════════════════════════════════════════════════════════════
# Seed data — name fragments per category
# ═══════════════════════════════════════════════════════════════
CATALOG: dict[str, dict] = {
    # slug: (adjectives, nouns, price_range, weight)
    "shirts": {
        "adj": ["Classic", "Slim", "Premium", "Casual", "Oxford", "Linen", "Flannel", "Denim", "Cotton", "Vintage"],
        "noun": ["Shirt", "Button-Down", "Oxford Shirt", "Dress Shirt", "Polo"],
        "price": (25, 120),
        "weight": 80,
    },
    "trousers": {
        "adj": ["Slim", "Relaxed", "Tailored", "Cargo", "Chino", "Pleated", "Stretch"],
        "noun": ["Trousers", "Pants", "Chinos", "Slacks"],
        "price": (35, 180),
        "weight": 70,
    },
    "dresses": {
        "adj": ["Floral", "Elegant", "Summer", "Evening", "Casual", "Wrap", "Maxi"],
        "noun": ["Dress", "Gown", "Sundress"],
        "price": (45, 250),
        "weight": 60,
    },
    "jackets-coats": {
        "adj": ["Leather", "Denim", "Wool", "Puffer", "Bomber", "Trench", "Quilted"],
        "noun": ["Jacket", "Coat", "Parka", "Blazer"],
        "price": (80, 450),
        "weight": 50,
    },
    "sweaters": {
        "adj": ["Merino", "Cashmere", "Cable-Knit", "Chunky", "Lightweight"],
        "noun": ["Sweater", "Cardigan", "Pullover", "Hoodie"],
        "price": (40, 220),
        "weight": 50,
    },
    "activewear": {
        "adj": ["Performance", "Dry-Fit", "Compression", "Athletic", "Training"],
        "noun": ["Leggings", "Tank", "Shorts", "Tee", "Joggers"],
        "price": (25, 120),
        "weight": 60,
    },
    "sneakers": {
        "adj": ["Running", "Canvas", "Leather", "Sport", "Retro", "Skate"],
        "noun": ["Sneakers", "Trainers", "Running Shoes"],
        "price": (55, 220),
        "weight": 70,
    },
    "boots": {
        "adj": ["Chelsea", "Work", "Hiking", "Western", "Ankle"],
        "noun": ["Boots", "Boot"],
        "price": (75, 320),
        "weight": 50,
    },
    "sandals": {
        "adj": ["Sport", "Leather", "Beach", "Slide", "Strappy"],
        "noun": ["Sandals", "Flip-Flops"],
        "price": (20, 140),
        "weight": 40,
    },
    "formal-shoes": {
        "adj": ["Oxford", "Derby", "Loafer", "Monk-Strap"],
        "noun": ["Shoes", "Loafers", "Oxfords"],
        "price": (90, 380),
        "weight": 30,
    },
    "bags-backpacks": {
        "adj": ["Laptop", "Travel", "Leather", "Canvas", "Water-Resistant"],
        "noun": ["Backpack", "Bag", "Tote", "Messenger", "Duffel"],
        "price": (35, 280),
        "weight": 60,
    },
    "watches": {
        "adj": ["Smart", "Automatic", "Chronograph", "Digital", "Dress"],
        "noun": ["Watch"],
        "price": (55, 650),
        "weight": 50,
    },
    "jewelry": {
        "adj": ["Gold-Plated", "Sterling Silver", "Rose Gold", "Minimalist"],
        "noun": ["Necklace", "Bracelet", "Earrings", "Ring"],
        "price": (25, 320),
        "weight": 40,
    },
    "hats-caps": {
        "adj": ["Baseball", "Beanie", "Bucket", "Snapback", "Fedora"],
        "noun": ["Cap", "Hat", "Beanie"],
        "price": (15, 90),
        "weight": 30,
    },
    "headphones": {
        "adj": ["Wireless", "Noise-Cancelling", "Over-Ear", "In-Ear", "Studio"],
        "noun": ["Headphones", "Earbuds", "Headset"],
        "price": (35, 450),
        "weight": 60,
    },
    "smart-home": {
        "adj": ["Smart", "Wi-Fi", "Voice-Controlled"],
        "noun": ["Bulb", "Plug", "Camera", "Doorbell", "Thermostat"],
        "price": (25, 300),
        "weight": 40,
    },
    "computers": {
        "adj": ["Portable", "Wireless", "Ergonomic", "Mechanical", "RGB"],
        "noun": ["Mouse", "Keyboard", "Webcam", "Hub", "SSD"],
        "price": (30, 400),
        "weight": 50,
    },
    "mobile-accessories": {
        "adj": ["Magnetic", "Fast-Charging", "Slim", "Rugged", "Foldable"],
        "noun": ["Charger", "Case", "Stand", "Cable", "Holder"],
        "price": (15, 150),
        "weight": 60,
    },
    "cameras": {
        "adj": ["HD", "4K", "Portable", "Action", "Mirrorless"],
        "noun": ["Camera", "Webcam", "Tripod", "Gimbal"],
        "price": (45, 850),
        "weight": 30,
    },
    "fitness-equipment": {
        "adj": ["Adjustable", "Portable", "Non-Slip", "Pro"],
        "noun": ["Dumbbells", "Yoga Mat", "Resistance Bands", "Jump Rope", "Foam Roller"],
        "price": (15, 250),
        "weight": 70,
    },
    "outdoor-gear": {
        "adj": ["Waterproof", "Compact", "Insulated", "Heavy-Duty"],
        "noun": ["Bottle", "Tent", "Sleeping Bag", "Lantern", "Cooler"],
        "price": (20, 350),
        "weight": 50,
    },
    "cycling": {
        "adj": ["Carbon", "Aluminum", "LED", "Waterproof"],
        "noun": ["Helmet", "Light", "Lock", "Pump", "Gloves"],
        "price": (25, 220),
        "weight": 40,
    },
    # ─── Fallback for top-level-only ───
    "clothing": {
        "adj": ["Classic", "Modern", "Essential", "Everyday"],
        "noun": ["Apparel", "Garment", "Item"],
        "price": (25, 150),
        "weight": 20,
    },
    "footwear": {
        "adj": ["Comfort", "Casual", "Sport"],
        "noun": ["Shoe", "Footwear"],
        "price": (40, 200),
        "weight": 15,
    },
    "accessories": {
        "adj": ["Essential", "Premium", "Compact"],
        "noun": ["Accessory", "Item"],
        "price": (15, 120),
        "weight": 15,
    },
    "electronics": {
        "adj": ["Wireless", "Portable", "Smart"],
        "noun": ["Device", "Gadget"],
        "price": (30, 300),
        "weight": 15,
    },
    "home-kitchen": {
        "adj": ["Stainless Steel", "Non-Stick", "Ceramic"],
        "noun": ["Pan", "Knife", "Mug", "Cutting Board", "Container"],
        "price": (20, 180),
        "weight": 30,
    },
    "sports-outdoors": {
        "adj": ["Pro", "Training", "All-Terrain"],
        "noun": ["Equipment", "Gear", "Kit"],
        "price": (25, 250),
        "weight": 20,
    },
    "beauty": {
        "adj": ["Hydrating", "Vitamin C", "Anti-Aging", "Natural"],
        "noun": ["Serum", "Cream", "Cleanser", "Mask", "Lip Balm"],
        "price": (12, 95),
        "weight": 30,
    },
    "toys-games": {
        "adj": ["Educational", "Interactive", "Classic", "Family"],
        "noun": ["Puzzle", "Board Game", "Building Set", "Action Figure"],
        "price": (15, 130),
        "weight": 30,
    },
    "books": {
        "adj": ["Bestseller", "Classic", "Illustrated", "Pocket"],
        "noun": ["Novel", "Guide", "Cookbook", "Journal"],
        "price": (8, 65),
        "weight": 30,
    },
    "pet-supplies": {
        "adj": ["Durable", "Chew-Resistant", "Cozy", "Interactive"],
        "noun": ["Toy", "Bed", "Bowl", "Collar", "Leash"],
        "price": (10, 90),
        "weight": 30,
    },
}


def make_sku(cat_slug: str, idx: int) -> str:
    prefix = "".join(c for c in cat_slug.upper() if c.isalnum())[:6] or "GEN"
    return f"BULK-{prefix}-{idx:04d}"


def make_image_url(sku: str) -> str:
    """Deterministic image URL — same SKU always → same image."""
    return f"https://picsum.photos/seed/{sku}/400/400"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rng = random.Random(args.seed)

    db = SessionLocal()
    try:
        # ─── Idempotent: delete existing BULK- products ───
        existing_bulk = db.execute(
            select(Product.id).where(Product.sku.like("BULK-%"))
        ).scalars().all()

        if existing_bulk:
            print(f"🧹 Removing {len(existing_bulk)} existing BULK- products…")
            # CASCADE on inventory FK handles inventories
            db.execute(delete(Product).where(Product.sku.like("BULK-%")))
            db.commit()

        # ─── Load categories by slug ───
        categories = {
            c.slug: c.id
            for c in db.execute(select(Category)).scalars().all()
        }
        print(f"📚 Loaded {len(categories)} categories.")

        # ─── Build weighted list of slugs ───
        weighted: list[str] = []
        for slug, cfg in CATALOG.items():
            if slug not in categories:
                continue
            weighted.extend([slug] * cfg["weight"])

        if not weighted:
            raise RuntimeError(
                "No matching categories found. Run seed_categories_bulk.py first."
            )

        # ─── Generate products ───
        batch_size = 100
        total_created = 0
        per_cat_count: dict[str, int] = {}

        while total_created < args.count:
            product_batch: list[Product] = []
            inventory_batch: list[Inventory] = []

            for _ in range(min(batch_size, args.count - total_created)):
                cat_slug = rng.choice(weighted)
                cfg = CATALOG[cat_slug]
                cat_id = categories[cat_slug]

                n = per_cat_count.get(cat_slug, 0) + 1
                per_cat_count[cat_slug] = n

                sku = make_sku(cat_slug, n + 1000)
                name = f"{rng.choice(cfg['adj'])} {rng.choice(cfg['noun'])}"

                lo, hi = cfg["price"]
                price = Decimal(str(round(rng.uniform(lo, hi), 2)))

                product = Product(
                    name=name,
                    sku=sku,
                    description=(
                        f"{name} — premium quality. Category: "
                        f"{cat_slug.replace('-', ' ').title()}."
                    ),
                    price=price,
                    category_id=cat_id,
                    image_url=make_image_url(sku),
                    is_active=True,
                    review_status=ProductReviewStatus.APPROVED,
                )
                product_batch.append(product)

                # Inventory — 0-500 units, some low-stock for realism
                qty_roll = rng.random()
                if qty_roll < 0.10:
                    qty = rng.randint(0, 5)       # 10% low stock
                elif qty_roll < 0.30:
                    qty = rng.randint(6, 25)      # 20% mid
                else:
                    qty = rng.randint(26, 500)    # 70% healthy
                threshold = rng.choice([3, 5, 10, 15, 20])

                # We need product.id — but batch insert hasn't assigned yet.
                # Solution: two-phase insert (commit products first).
                # Alternative: rely on SQLAlchemy relationship.
                # Simplest: flush after product add to get IDs.
                # ─── Simpler approach: add product, flush, then inventory ───
                db.add(product)
                db.flush()  # gets ID

                inventory = Inventory(
                    product_id=product.id,
                    location="default",
                    quantity=qty,
                    low_stock_threshold=threshold,
                )
                db.add(inventory)

            db.commit()
            total_created += len(product_batch)
            print(f"  → {total_created}/{args.count} products created")

        # ─── Summary ───
        print("\n" + "═" * 60)
        print(f"✅ Bulk seeding complete!")
        print(f"   Products:    {total_created}")
        print(f"   Categories:  {len(per_cat_count)} used")
        print("═" * 60)
        print("Top categories by product count:")
        for slug, count in sorted(
            per_cat_count.items(), key=lambda x: -x[1]
        )[:10]:
            print(f"   {slug:25s} {count}")

    except Exception as exc:
        db.rollback()
        print(f"❌ Error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
