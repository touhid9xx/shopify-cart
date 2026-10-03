"""Admin product endpoints — create, update, delete, upload+classify, review."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.config import get_settings
from shopify_cart.core.pagination import (
    Page,
    PageParams,
    build_page,
    get_page_params,
    paginate_query,
)
from shopify_cart.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.ml.predict import get_predictor
from shopify_cart.models.category import Category
from shopify_cart.models.product import Product, ProductReviewStatus
from shopify_cart.schemas.admin_upload import (
    NeedsReviewResponse,
    ProductCreatedResponse,
)
from shopify_cart.schemas.product import (
    ProductCreate,
    ProductRead,
    ProductReadWithReview,
    ProductUpdate,
)
from shopify_cart.services.autocat_service import AutoCategorizationService
from shopify_cart.services.product_service import ProductService

router = APIRouter(prefix="/admin/products", tags=["admin:products"])
logger = get_logger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Dependency helpers
# ══════════════════════════════════════════════════════════════════════
def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


# ══════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ══════════════════════════════════════════════════════════════════════
# Review-workflow schemas (local to this router)
# ══════════════════════════════════════════════════════════════════════
class ReviewActionPayload(BaseModel):
    """Optional notes for approve."""

    notes: str | None = Field(default=None, max_length=2000)


class RejectPayload(BaseModel):
    """Required reason for rejection."""

    reason: str = Field(min_length=3, max_length=500)


class RecategorizePayload(BaseModel):
    """Admin override of the ML-predicted category."""

    category_id: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class ReviewActionResponse(BaseModel):
    """Result of approve/reject/recategorize."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    review_status: ProductReviewStatus
    reviewed_by: int | None
    reviewed_at: datetime | None
    review_notes: str | None


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════
async def _publish_review_event(
    producer: KafkaProducer,
    topic: str,
    payload: dict[str, Any],
) -> None:
    """Publish a review-workflow event; log and swallow errors."""
    try:
        await producer.publish(topic, payload)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "review_event_publish_failed",
            topic=topic,
            error=str(exc),
        )


# ══════════════════════════════════════════════════════════════════════
# CRUD — create
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (admin only, manual category)",
)
async def create_product(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    payload: ProductCreate,
) -> ProductRead:
    product = await ProductService.create(db, producer, payload)
    return ProductRead.model_validate(product)


# ══════════════════════════════════════════════════════════════════════
# REVIEW QUEUE — must be declared BEFORE any GET /{product_id}
# ══════════════════════════════════════════════════════════════════════
@router.get(
    "/pending-review",
    response_model=Page[ProductReadWithReview],
    summary="List products awaiting admin review",
)
def list_pending_review(
    db: DbSession,
    _admin: CurrentAdmin,
    params: Annotated[PageParams, Depends(get_page_params)],
) -> Page[ProductReadWithReview]:
    """Paginated list of products with review_status = pending.

    Ordered oldest-first so admins work the queue FIFO.
    """
    stmt = (
        select(Product)
        .where(Product.review_status == ProductReviewStatus.PENDING)
        .order_by(Product.created_at.asc())
        .options(selectinload(Product.category))
    )
    rows: list[Product]
    total: int
    rows, total = paginate_query(db, stmt, params)
    return build_page(
        [ProductReadWithReview.model_validate(r) for r in rows],
        total,
        params,
    )


# ══════════════════════════════════════════════════════════════════════
# REVIEW ACTIONS — approve / reject / recategorize
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/{product_id}/approve",
    response_model=ReviewActionResponse,
    summary="Approve a pending product",
)
async def approve_product(
    db: DbSession,
    producer: ProducerDep,
    admin: CurrentAdmin,
    product_id: int,
    payload: ReviewActionPayload | None = None,
) -> ReviewActionResponse:
    """Mark a pending product as approved.

    - Sets review_status → APPROVED
    - Records reviewer + timestamp
    - Re-activates the product
    - Publishes `product.approved` to Kafka (best-effort)
    """
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found.")
    if product.review_status != ProductReviewStatus.PENDING:
        raise ConflictError(
            f"Product {product_id} is not pending (current: {product.review_status})."
        )

    reviewed_at = datetime.now(UTC)
    product.review_status = ProductReviewStatus.APPROVED
    product.reviewed_by = admin.id
    product.reviewed_at = reviewed_at
    product.review_notes = payload.notes if payload else None
    product.is_active = True

    db.commit()
    db.refresh(product)

    await _publish_review_event(
        producer,
        "product.approved",
        {
            "product_id": product.id,
            "sku": product.sku,
            "reviewed_by": admin.id,
            "reviewed_at": reviewed_at.isoformat(),
        },
    )

    logger.info(
        "product_approved",
        product_id=product.id,
        admin_id=admin.id,
        sku=product.sku,
    )
    return ReviewActionResponse.model_validate(product)


@router.post(
    "/{product_id}/reject",
    response_model=ReviewActionResponse,
    summary="Reject a pending product",
)
async def reject_product(
    db: DbSession,
    producer: ProducerDep,
    admin: CurrentAdmin,
    product_id: int,
    payload: RejectPayload,
) -> ReviewActionResponse:
    """Mark a pending product as rejected.

    - Sets review_status → REJECTED
    - Records reviewer + timestamp + reason
    - Deactivates the product
    - Publishes `product.rejected` to Kafka (best-effort)
    """
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found.")
    if product.review_status != ProductReviewStatus.PENDING:
        raise ConflictError(
            f"Product {product_id} is not pending (current: {product.review_status})."
        )

    reviewed_at = datetime.now(UTC)
    product.review_status = ProductReviewStatus.REJECTED
    product.reviewed_by = admin.id
    product.reviewed_at = reviewed_at
    product.review_notes = payload.reason
    product.is_active = False  # hide from customers

    db.commit()
    db.refresh(product)

    await _publish_review_event(
        producer,
        "product.rejected",
        {
            "product_id": product.id,
            "sku": product.sku,
            "reason": payload.reason,
            "reviewed_by": admin.id,
            "reviewed_at": reviewed_at.isoformat(),
        },
    )

    logger.info(
        "product_rejected",
        product_id=product.id,
        admin_id=admin.id,
        reason=payload.reason,
    )
    return ReviewActionResponse.model_validate(product)


@router.patch(
    "/{product_id}/recategorize",
    response_model=ReviewActionResponse,
    summary="Override ML category and approve",
)
async def recategorize_product(
    db: DbSession,
    producer: ProducerDep,
    admin: CurrentAdmin,
    product_id: int,
    payload: RecategorizePayload,
) -> ReviewActionResponse:
    """Change the product's category and mark it approved.

    Used when ML predicted a category but the admin knows better.
    Records the previous category in the Kafka event for audit.
    """
    product = db.get(Product, product_id)
    if product is None:
        raise NotFoundError(f"Product {product_id} not found.")

    category = db.get(Category, payload.category_id)
    if category is None:
        raise NotFoundError(f"Category {payload.category_id} not found.")

    previous_category_id = product.category_id
    reviewed_at = datetime.now(UTC)

    product.category_id = category.id
    product.review_status = ProductReviewStatus.APPROVED
    product.reviewed_by = admin.id
    product.reviewed_at = reviewed_at
    if payload.notes is not None:
        # Preserve any existing review_notes if the admin didn't send new ones
        product.review_notes = payload.notes
    product.is_active = True

    db.commit()
    db.refresh(product)

    await _publish_review_event(
        producer,
        "product.recategorized",
        {
            "product_id": product.id,
            "sku": product.sku,
            "from_category_id": previous_category_id,
            "to_category_id": product.category_id,
            "to_category_slug": category.slug,
            "reviewed_by": admin.id,
            "reviewed_at": reviewed_at.isoformat(),
        },
    )

    logger.info(
        "product_recategorized",
        product_id=product.id,
        admin_id=admin.id,
        from_category_id=previous_category_id,
        new_category=category.slug,
    )
    return ReviewActionResponse.model_validate(product)


# ══════════════════════════════════════════════════════════════════════
# CRUD — update / delete
# ══════════════════════════════════════════════════════════════════════
@router.put(
    "/{product_id}",
    response_model=ProductRead,
    summary="Update a product (admin only)",
)
async def update_product(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    product_id: int,
    payload: ProductUpdate,
) -> ProductRead:
    product = await ProductService.update(db, producer, product_id, payload)
    return ProductRead.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,  # 204 must not have a response body
    summary="Soft-delete a product (admin only)",
)
async def delete_product(
    product_id: int,
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
) -> None:
    await ProductService.delete(db, producer, product_id, hard=False)
    return None


# ══════════════════════════════════════════════════════════════════════
# UPLOAD + ML auto-categorize
# ══════════════════════════════════════════════════════════════════════
@router.post(
    "/upload",
    response_model=ProductCreatedResponse | NeedsReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload a product image and auto-categorize it via the ML model",
)
async def upload_and_categorize(
    db: DbSession,
    producer: ProducerDep,
    _admin: CurrentAdmin,
    image: Annotated[
        UploadFile,
        File(description="Product image (jpg/png/webp, max 10MB)"),
    ],
    name: Annotated[str, Form(min_length=1, max_length=255)],
    price: Annotated[str, Form(description="Price as string, e.g. '19.99'")],
    sku: Annotated[str | None, Form(max_length=64)] = None,
    description: Annotated[str | None, Form(max_length=10_000)] = None,
    image_url: Annotated[str | None, Form(max_length=512)] = None,
    location: Annotated[str, Form(max_length=80)] = "default",
    initial_quantity: Annotated[int, Form(ge=0)] = 0,
    low_stock_threshold: Annotated[int, Form(ge=0)] = 5,
    force_category_slug: Annotated[
        str | None,
        Form(
            max_length=120,
            description=(
                "Optional. If provided, skip ML auto-assign and use this "
                "category slug (for admin override after needs_review)."
            ),
        ),
    ] = None,
) -> ProductCreatedResponse | NeedsReviewResponse:
    """Upload a product image, run ML classification, and create the product.

    Returns either `ProductCreatedResponse` (high confidence) or
    `NeedsReviewResponse` (low confidence or no matching category).
    """
    # ---- Validate image ----
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported content type {image.content_type!r}. "
            f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
        )
    image_bytes = await image.read()
    if not image_bytes:
        raise ValidationError("Empty image file uploaded.")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValidationError(f"File too large ({len(image_bytes)} bytes, max {MAX_UPLOAD_BYTES}).")

    # ---- Parse price ----
    try:
        price_dec = Decimal(price).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Invalid price {price!r}: {exc}") from exc
    if price_dec <= 0:
        raise ValidationError("Price must be greater than 0.")

    # ---- Get predictor (lazy-load if startup load failed) ----
    predictor = get_predictor()
    if not predictor.is_loaded:
        predictor.load()

    # ---- Run the service ----
    outcome = await AutoCategorizationService.process_upload(
        db,
        producer,
        predictor,
        image_bytes=image_bytes,
        name=name.strip(),
        price=price_dec,
        sku=sku.strip() if sku else None,
        description=description,
        image_url=image_url,
        location=location,
        initial_quantity=initial_quantity,
        low_stock_threshold=low_stock_threshold,
        force_category_slug=(force_category_slug.strip() if force_category_slug else None),
    )

    settings = get_settings()
    return AutoCategorizationService.to_response(
        outcome,
        settings_confidence_threshold=settings.model_confidence_threshold,
    )
