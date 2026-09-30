"""Pydantic schemas for the prediction endpoint."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PredictionItem(BaseModel):
    """One (category, confidence) pair."""

    model_config = ConfigDict(from_attributes=True)

    category: str
    category_index: int
    confidence: float = Field(ge=0.0, le=1.0)


class PredictionResponse(BaseModel):
    """Response from POST /predict."""

    # Allow ``model_*`` field names (model_name, model_version, model_stage)
    # without triggering Pydantic's protected-namespace warning.
    model_config = ConfigDict(
        from_attributes=True,
        protected_namespaces=(),
    )

    category: str = Field(description="Top-1 predicted category")
    confidence: float = Field(ge=0.0, le=1.0)
    top_k: list[PredictionItem] = Field(default_factory=list)
    model_name: str
    model_version: str | None = None
    model_stage: str | None = None
    cached: bool = Field(default=False, description="True if served from cache")
    inference_ms: float = Field(ge=0.0)
