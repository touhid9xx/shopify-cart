"""
Auto-categorization service — the core feature.

Flow for POST /admin/products/upload:
  1. Save image file (or use provided image_url).
  2. Call ML predictor on image bytes.
  3. If confidence >= threshold:
       - Map ML class → Category slug (with fallback mapping).
       - Atomically create Product + Inventory + publish event.
       - Return {status: "created", product, category, confidence}.
     Else:
       - Return {status: "needs_review", suggestions=[top_k], confidence}.
  4. All DB writes in a single transaction; Kafka publish AFTER commit.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from shopify_cart.config import get_settings
from shopify_cart.exceptions import ConflictError, MLModelError, ValidationError
from shopify_cart.kafka.events import ProductCreatedEvent
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.ml.predict import CategoryPredictor, PredictionResult
from shopify_cart.models.category import Category
from shopify_cart.models.inventory import Inventory
from shopify_cart.models.product import Product, ProductReviewStatus
from shopify_cart.schemas.admin_upload import (
    NeedsReviewResponse,
    ProductCreatedResponse,
    TopSuggestion,
)

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# ML class name → Category slug mapping
# ----------------------------------------------------------------------
# ML classes (Milestone 12) come from the fashion-product-images-small
# dataset. They are Title_Case_with_underscores. Our Category table uses
# lowercase slugs with hyphens. This mapping normalizes both sides.
#
# Keys are ML class names (as produced by the classifier).
# Values are Category slugs we expect in the DB.
# ----------------------------------------------------------------------
ML_CLASS_TO_SLUG: dict[str, str] = {
    # Direct mappings (ML class name == Category slug-ish)
    "Accessories": "accessories",
    "Apparel": "clothing",
    "Footwear": "footwear",
    "Personal_Care": "personal-care",
    # Fallbacks — if ML emits a finer-grained class in the future
    "Shirt": "shirt",
    "Trouser": "trouser",
    "Dress": "dress",
    "Jacket": "jacket",
    "Sweater": "sweater",
    "Shoe": "shoe",
    "Sandal": "sandal",
    "Boot": "boot",
    "Bag": "bag",
    "Hat": "hat",
    "Belt": "belt",
}


def _normalize_slug(text: str) -> str:
    """Lowercase, replace spaces/underscores with hyphens, strip non-alnum."""
    s = text.strip().lower().replace("_", "-").replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s


def resolve_category_from_ml_class(db: Session, ml_class: str) -> Category | None:
    """
    Map an ML class name to a Category ORM row.

    Strategy:
      1. Explicit mapping via ML_CLASS_TO_SLUG.
      2. Fallback: try normalized slug match on Category.slug.
      3. Fallback: try case-insensitive name match on Category.name.
      4. Return None if nothing matches (caller treats as needs_review).
    """
    # Step 1 — explicit map
    slug = ML_CLASS_TO_SLUG.get(ml_class)
    if slug is not None:
        cat = db.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()
        if cat is not None:
            return cat

    # Step 2 — normalized slug
    normalized = _normalize_slug(ml_class)
    cat = db.execute(select(Category).where(Category.slug == normalized)).scalar_one_or_none()
    if cat is not None:
        return cat

    # Step 3 — case-insensitive name match
    cat = db.execute(select(Category).where(Category.name.ilike(ml_class))).scalar_one_or_none()
    if cat is not None:
        return cat

    logger.warning("autocat_no_category_match", ml_class=ml_class)
    return None


# ----------------------------------------------------------------------
# Result types
# ----------------------------------------------------------------------
AutoCatStatus = Literal["created", "needs_review"]


@dataclass
class AutoCatOutcome:
    status: AutoCatStatus
    product: Product | None = None
    category: Category | None = None
    prediction: PredictionResult | None = None
    message: str = ""


# ----------------------------------------------------------------------
# Service
# ----------------------------------------------------------------------
class AutoCategorizationService:
    @staticmethod
    def _default_sku(prefix: str = "UPL") -> str:
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    @staticmethod
    def _suggestions_from_prediction(
        prediction: PredictionResult,
    ) -> list[TopSuggestion]:
        return [
            TopSuggestion(category=item.category, confidence=item.confidence)
            for item in prediction.top_k
        ]

    @staticmethod
    def _ensure_unique_sku(db: Session, sku: str) -> None:
        existing = db.execute(select(Product).where(Product.sku == sku)).scalar_one_or_none()
        if existing is not None:
            raise ConflictError(f"SKU {sku!r} already exists.")

    @staticmethod
    async def process_upload(
        db: Session,
        producer: KafkaProducer,
        predictor: CategoryPredictor,
        *,
        image_bytes: bytes,
        name: str,
        price: Decimal,
        sku: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        location: str = "default",
        initial_quantity: int = 0,
        low_stock_threshold: int = 5,
        force_category_slug: str | None = None,
    ) -> AutoCatOutcome:
        """
        Main entry point.

        `force_category_slug` lets an admin override the ML decision
        (used when the client previously received 'needs_review' and
        now resubmits with a chosen category).
        """
        settings = get_settings()

        # ---- 1) Validate inputs ----
        if not image_bytes and not image_url:
            raise ValidationError("Either an image upload or an image_url is required.")
        if price <= 0:
            raise ValidationError("Price must be greater than 0.")

        # ---- 2) Override path: admin provided a category slug ----
        if force_category_slug is not None:
            forced = db.execute(
                select(Category).where(Category.slug == force_category_slug)
            ).scalar_one_or_none()
            if forced is None:
                raise ValidationError(f"Category slug {force_category_slug!r} does not exist.")
            prediction: PredictionResult | None = None
            if image_bytes:
                try:
                    prediction = predictor.predict(image_bytes, top_k=settings.model_top_k)
                except MLModelError:
                    # Override path doesn't strictly need prediction
                    prediction = None
            return await AutoCategorizationService._create_product(
                db,
                producer,
                name=name,
                price=price,
                sku=sku,
                description=description,
                image_url=image_url,
                image_bytes=image_bytes,
                category=forced,
                location=location,
                initial_quantity=initial_quantity,
                low_stock_threshold=low_stock_threshold,
                prediction=prediction,
                force_reason="admin_override",
            )

        # ---- 3) ML prediction ----
        if not predictor.is_loaded:
            try:
                predictor.load()
            except MLModelError:
                raise

        try:
            prediction = predictor.predict(image_bytes, top_k=settings.model_top_k)
        except MLModelError:
            raise
        except Exception as exc:
            logger.exception("autocat_predict_failed")
            raise MLModelError(f"Prediction failed: {exc}") from exc

        threshold = settings.model_confidence_threshold
        logger.info(
            "autocat_prediction",
            category=prediction.category,
            confidence=round(prediction.confidence, 4),
            threshold=threshold,
            will_accept=prediction.confidence >= threshold,
        )

        # ---- 4a) Low confidence → needs_review ----
        if prediction.confidence < threshold:
            return AutoCatOutcome(
                status="needs_review",
                prediction=prediction,
                message=(
                    f"Top prediction {prediction.category!r} has confidence "
                    f"{prediction.confidence:.2f} < threshold {threshold:.2f}. "
                    f"Please confirm or override."
                ),
            )

        # ---- 4b) High confidence → resolve category ----
        category = resolve_category_from_ml_class(db, prediction.category)
        if category is None:
            # ML was confident but we have no matching Category row —
            # treat as needs_review so admin can pick.
            return AutoCatOutcome(
                status="needs_review",
                prediction=prediction,
                message=(
                    f"Predicted {prediction.category!r} but no matching "
                    f"category exists in the catalog."
                ),
            )

        # ---- 5) Create product atomically ----
        return await AutoCategorizationService._create_product(
            db,
            producer,
            name=name,
            price=price,
            sku=sku,
            description=description,
            image_url=image_url,
            image_bytes=image_bytes,
            category=category,
            location=location,
            initial_quantity=initial_quantity,
            low_stock_threshold=low_stock_threshold,
            prediction=prediction,
            force_reason="auto",
        )

    # ------------------------------------------------------------------
    # Atomic product creation
    # ------------------------------------------------------------------
    @staticmethod
    async def _create_product(
        db: Session,
        producer: KafkaProducer,
        *,
        name: str,
        price: Decimal,
        sku: str | None,
        description: str | None,
        image_url: str | None,
        image_bytes: bytes,
        category: Category,
        location: str,
        initial_quantity: int,
        low_stock_threshold: int,
        prediction: PredictionResult | None,
        force_reason: str,
    ) -> AutoCatOutcome:
        # Resolve SKU
        final_sku = sku or AutoCategorizationService._default_sku(
            prefix=_normalize_slug(category.slug)[:4].upper() or "UPL"
        )
        AutoCategorizationService._ensure_unique_sku(db, final_sku)

        # Resolve image URL — if bytes provided and no URL, we save locally.
        # In production, you'd upload to S3/GCS here. Local path is fine
        # for this milestone (URL is stored, file is optional).
        stored_url = image_url
        if stored_url is None and image_bytes:
            stored_url = _save_uploaded_image(image_bytes)

        # ----- Atomic transaction: product + inventory -----
        try:
            # ── In _create_product, normalize ml_category_slug to a real slug ──
            product = Product(
                name=name,
                sku=final_sku,
                description=description,
                price=price,
                category_id=category.id,
                image_url=stored_url,
                is_active=True,
                # ── Review workflow ──
                review_status=ProductReviewStatus.PENDING,
                ml_category_slug=(
                    _normalize_slug(prediction.category) if prediction else None
                ),  # ← was: prediction.category
                ml_confidence=(Decimal(str(prediction.confidence)) if prediction else None),
            )
            db.add(product)
            db.flush()  # assigns id

            inv = Inventory(
                product_id=product.id,
                location=location,
                quantity=max(0, initial_quantity),
                low_stock_threshold=max(0, low_stock_threshold),
            )
            db.add(inv)

            db.commit()
        except Exception:
            db.rollback()
            logger.exception("autocat_create_failed", sku=final_sku)
            raise

        db.refresh(product)

        # ----- Event AFTER commit -----
        event = ProductCreatedEvent(
            product_id=product.id,
            name=product.name,
            sku=product.sku,
            category_id=product.category_id,
            price=product.price,
            image_url=product.image_url,
        )
        await producer.publish("product.created", event, key=str(product.id))

        # ── Add review_status to the success log ──
        logger.info(
            "autocat_product_created",
            product_id=product.id,
            sku=product.sku,
            category_slug=category.slug,
            review_status=product.review_status.value,  # NEW
            reason=force_reason,
            confidence=(round(prediction.confidence, 4) if prediction is not None else None),
        )

        return AutoCatOutcome(
            status="created",
            product=product,
            category=category,
            prediction=prediction,
            message="Product created and categorized.",
        )

    # ------------------------------------------------------------------
    # Response builders
    # ------------------------------------------------------------------
    @staticmethod
    def to_response(
        outcome: AutoCatOutcome,
        *,
        settings_confidence_threshold: float,
    ) -> ProductCreatedResponse | NeedsReviewResponse:
        if outcome.status == "created":
            assert outcome.product is not None
            assert outcome.category is not None
            return ProductCreatedResponse(
                status="created",
                product_id=outcome.product.id,
                name=outcome.product.name,
                sku=outcome.product.sku,
                price=outcome.product.price,
                category_id=outcome.category.id,
                category_slug=outcome.category.slug,
                category_name=outcome.category.name,
                image_url=outcome.product.image_url,
                confidence=(
                    outcome.prediction.confidence if outcome.prediction is not None else None
                ),
                ml_category=(
                    outcome.prediction.category if outcome.prediction is not None else None
                ),
                message=outcome.message,
            )

        # needs_review
        assert outcome.prediction is not None
        return NeedsReviewResponse(
            status="needs_review",
            confidence=outcome.prediction.confidence,
            threshold=settings_confidence_threshold,
            ml_category=outcome.prediction.category,
            suggestions=AutoCategorizationService._suggestions_from_prediction(outcome.prediction),
            message=outcome.message,
        )


# ----------------------------------------------------------------------
# Image storage helper
# ----------------------------------------------------------------------
def _save_uploaded_image(image_bytes: bytes, *, subdir: str = "uploads") -> str:
    """
    Persist an uploaded image to disk and return a relative URL.

    Production note: replace with S3/GCS upload and return the public URL.
    """
    ext = _guess_extension(image_bytes)
    digest = hashlib.sha256(image_bytes).hexdigest()[:16]
    filename = f"{digest}{ext}"
    base_dir = Path("data") / subdir
    base_dir.mkdir(parents=True, exist_ok=True)
    filepath = base_dir / filename
    if not filepath.exists():
        filepath.write_bytes(image_bytes)
    # Relative URL served by a static mount in the future
    return f"/static/{subdir}/{filename}"


def _guess_extension(image_bytes: bytes) -> str:
    """Guess image extension from magic bytes."""
    if image_bytes[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return ".webp"
    return ".bin"
