"""Unit tests for prediction service — no MLflow, no GPU."""

from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
import torch
from PIL import Image

from shopify_cart.exceptions import MLModelError, ValidationError
from shopify_cart.ml.predict import (
    CategoryPredictor,
    PredictionItem,
    PredictionResult,
    _LRUPredictionCache,
    _reset_predictor_for_tests,
)


def _make_test_image_bytes(size: tuple[int, int] = (100, 100)) -> bytes:
    img = Image.new("RGB", size, color=(128, 64, 200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ----------------------------------------------------------------------
# LRU cache
# ----------------------------------------------------------------------
def test_lru_cache_put_get() -> None:
    cache = _LRUPredictionCache(max_size=3)
    item = PredictionResult(
        category="shirt",
        confidence=0.9,
        top_k=[],
        model_name="m",
        model_version="1",
        model_stage="Production",
        cached=False,
        inference_ms=10.0,
    )
    cache.put("k1", item)
    assert cache.get("k1") == item
    assert cache.get("missing") is None


def test_lru_cache_eviction() -> None:
    cache = _LRUPredictionCache(max_size=2)
    item = PredictionResult(
        category="x",
        confidence=0.5,
        top_k=[],
        model_name="m",
        model_version=None,
        model_stage=None,
        cached=False,
        inference_ms=1.0,
    )
    cache.put("a", item)
    cache.put("b", item)
    cache.put("c", item)  # evicts "a"
    assert cache.get("a") is None
    assert cache.get("b") == item
    assert cache.get("c") == item


def test_lru_cache_clear() -> None:
    cache = _LRUPredictionCache(max_size=5)
    cache.put("x", MagicMock())
    cache.clear()
    assert len(cache) == 0


# ----------------------------------------------------------------------
# Predictor — not loaded
# ----------------------------------------------------------------------
def test_predict_before_load_raises() -> None:
    _reset_predictor_for_tests()
    p = CategoryPredictor()
    with pytest.raises(MLModelError):
        p.predict(_make_test_image_bytes())


# ----------------------------------------------------------------------
# Predictor — mocked model
# ----------------------------------------------------------------------
def _make_predictor_with_mock_model(num_classes: int = 4) -> CategoryPredictor:
    _reset_predictor_for_tests()
    p = CategoryPredictor()

    class FakeModel(torch.nn.Module):
        def __init__(self, n: int) -> None:
            super().__init__()
            self.n = n

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            # Deterministic logits: prefer class 2
            logits = torch.zeros(x.shape[0], self.n, device=x.device)
            logits[:, 2] = 3.0
            logits[:, 0] = 1.5
            logits[:, 1] = 0.5
            return logits

    p._model = FakeModel(num_classes)  # type: ignore[assignment]
    p._classes = ["shirt", "trouser", "shoe", "bag"]
    p._version = "1"
    p._stage = "Production"
    p._loaded = True
    return p


def test_predict_top_k_order() -> None:
    p = _make_predictor_with_mock_model()
    result = p.predict(_make_test_image_bytes(), top_k=3)
    assert result.category == "shoe"  # class index 2
    assert len(result.top_k) == 3
    assert result.top_k[0].category == "shoe"
    assert result.top_k[0].confidence > result.top_k[1].confidence


def test_predict_caches_result() -> None:
    p = _make_predictor_with_mock_model()
    data = _make_test_image_bytes()
    r1 = p.predict(data, top_k=3)
    r2 = p.predict(data, top_k=3)
    assert r1.cached is False
    assert r2.cached is True
    assert r1.category == r2.category


def test_predict_different_images_not_cached() -> None:
    p = _make_predictor_with_mock_model()
    a = _make_test_image_bytes((50, 50))
    b = _make_test_image_bytes((60, 60))
    p.predict(a)
    result_b = p.predict(b)
    assert result_b.cached is False


def test_predict_invalid_image_raises_validation_error() -> None:
    p = _make_predictor_with_mock_model()
    with pytest.raises(ValidationError):
        p.predict(b"not-an-image")


def test_predict_top_k_clamped_to_num_classes() -> None:
    p = _make_predictor_with_mock_model(num_classes=4)
    result = p.predict(_make_test_image_bytes(), top_k=100)
    assert len(result.top_k) == 4


def test_clear_cache() -> None:
    p = _make_predictor_with_mock_model()
    data = _make_test_image_bytes()
    p.predict(data)
    p.clear_cache()
    result = p.predict(data)
    assert result.cached is False


# ----------------------------------------------------------------------
# get_predictor singleton
# ----------------------------------------------------------------------
def test_get_predictor_returns_singleton() -> None:
    from shopify_cart.ml.predict import get_predictor

    _reset_predictor_for_tests()
    a = get_predictor()
    b = get_predictor()
    assert a is b


# ----------------------------------------------------------------------
# load_predictor_at_startup — fail-safe
# ----------------------------------------------------------------------
def test_load_predictor_at_startup_failsafe() -> None:
    from shopify_cart.ml.predict import load_predictor_at_startup

    _reset_predictor_for_tests()

    # Simulate MLflow being down by patching the underlying _load_unlocked
    with patch.object(
        CategoryPredictor,
        "_load_unlocked",
        side_effect=MLModelError("MLflow unavailable"),
    ):
        p = load_predictor_at_startup()
        assert p.is_loaded is False


# ----------------------------------------------------------------------
# PredictionItem frozen
# ----------------------------------------------------------------------
def test_prediction_item_is_frozen() -> None:
    item = PredictionItem(category="x", category_index=0, confidence=0.5)
    with pytest.raises((AttributeError, Exception)):
        item.category = "y"  # type: ignore[misc]
