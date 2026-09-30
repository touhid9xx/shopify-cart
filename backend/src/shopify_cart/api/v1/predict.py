"""Prediction endpoint — upload image, get category."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from shopify_cart.exceptions import ValidationError
from shopify_cart.logging_config import get_logger
from shopify_cart.ml.predict import get_predictor
from shopify_cart.schemas.predict import PredictionItem, PredictionResponse

router = APIRouter(prefix="/predict", tags=["ml"])
logger = get_logger(__name__)


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post(
    "",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify a product image into a category",
)
async def predict(
    image: Annotated[UploadFile, File(description="Product image (jpg/png/webp)")],
    top_k: Annotated[int, Query(ge=1, le=10)] = 3,
) -> PredictionResponse:
    # Validate content type
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported content type {image.content_type!r}. "
            f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
        )

    # Read + size guard
    data = await image.read()
    if not data:
        raise ValidationError("Empty file uploaded.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValidationError(f"File too large ({len(data)} bytes, max {MAX_UPLOAD_BYTES}).")

    predictor = get_predictor()
    if not predictor.is_loaded:
        # Lazy attempt — the startup load might have failed earlier
        predictor.load()  # raises MLModelError on failure

    result = predictor.predict(data, top_k=top_k)

    return PredictionResponse(
        category=result.category,
        confidence=result.confidence,
        top_k=[
            PredictionItem(
                category=item.category,
                category_index=item.category_index,
                confidence=item.confidence,
            )
            for item in result.top_k
        ],
        model_name=result.model_name,
        model_version=result.model_version,
        model_stage=result.model_stage,
        cached=result.cached,
        inference_ms=result.inference_ms,
    )


@router.post(
    "/reset-cache",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,  # ← FIX: 204 must not have a body
    summary="Clear the prediction cache (admin/dev use)",
)
async def reset_cache() -> None:
    get_predictor().clear_cache()
