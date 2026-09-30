"""Admin product endpoints — create, update, delete, upload+classify."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Request,
    UploadFile,
    status,
)

from shopify_cart.api.deps import CurrentAdmin, DbSession
from shopify_cart.config import get_settings
from shopify_cart.exceptions import ValidationError
from shopify_cart.kafka.producer import KafkaProducer
from shopify_cart.logging_config import get_logger
from shopify_cart.ml.predict import get_predictor
from shopify_cart.schemas.admin_upload import (
    NeedsReviewResponse,
    ProductCreatedResponse,
)
from shopify_cart.schemas.product import ProductCreate, ProductRead, ProductUpdate
from shopify_cart.services.autocat_service import AutoCategorizationService
from shopify_cart.services.product_service import ProductService

router = APIRouter(prefix="/admin/products", tags=["admin:products"])
logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Dependency helpers
# ----------------------------------------------------------------------
def get_producer(request: Request) -> KafkaProducer:
    return request.app.state.kafka_producer  # type: ignore[no-any-return]


ProducerDep = Annotated[KafkaProducer, Depends(get_producer)]


# Allowed content types for uploads (mirrors /predict)
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


# ----------------------------------------------------------------------
# Existing CRUD (unchanged from Milestone 6)
# ----------------------------------------------------------------------
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


# ----------------------------------------------------------------------
# NEW: ML auto-categorization on upload
# ----------------------------------------------------------------------
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

    # ---- Parse price (Form gives str) ----
    try:
        price_dec = Decimal(price).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Invalid price {price!r}: {exc}") from exc
    if price_dec <= 0:
        raise ValidationError("Price must be greater than 0.")

    # ---- Get predictor ----
    predictor = get_predictor()
    if not predictor.is_loaded:
        # Try once more (startup might have failed earlier)
        predictor.load()

    # ---- Run service ----
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
        force_category_slug=force_category_slug.strip() if force_category_slug else None,
    )

    settings = get_settings()
    return AutoCategorizationService.to_response(
        outcome,
        settings_confidence_threshold=settings.model_confidence_threshold,
    )
