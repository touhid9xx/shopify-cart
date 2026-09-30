"""Pydantic schemas for admin product upload + auto-categorization."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TopSuggestion(BaseModel):
    """A single suggested category with confidence."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProductCreatedResponse(BaseModel):
    """Response when ML is confident (or admin overrode)."""

    status: str = "created"
    product_id: int
    name: str
    sku: str
    price: Decimal
    category_id: int
    category_slug: str
    category_name: str
    image_url: str | None
    confidence: float | None = None
    ml_category: str | None = None
    message: str = "Product created."


class NeedsReviewResponse(BaseModel):
    """Response when ML confidence is below threshold."""

    status: str = "needs_review"
    confidence: float
    threshold: float
    ml_category: str
    suggestions: list[TopSuggestion] = Field(default_factory=list)
    message: str = "Confidence below threshold. Please confirm or override."


# Union used as response_model in FastAPI with union discrimination
AutoCategorizeResponse = ProductCreatedResponse | NeedsReviewResponse
