"""Integration tests for /predict endpoint.

These require:
  - MySQL (for app startup consistency)
  - MLflow tracking server running
  - A registered model in the registry

Skip if any unavailable.
"""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from shopify_cart.ml.predict import get_predictor


def _make_png_bytes() -> bytes:
    img = Image.new("RGB", (80, 80), color=(200, 150, 100))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _predictor_ready() -> bool:
    try:
        p = get_predictor()
        if not p.is_loaded:
            p.load()
        return p.is_loaded
    except Exception:  # noqa: BLE001
        return False


@pytest.fixture(autouse=True)
def _require_model() -> None:
    if not _predictor_ready():
        pytest.skip("MLflow registry / model not available")


def test_predict_returns_category(client: TestClient) -> None:
    files = {"image": ("test.png", _make_png_bytes(), "image/png")}
    r = client.post("/api/v1/predict?top_k=3", files=files)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "category" in body
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["top_k"]) == 3
    assert body["model_name"]


def test_predict_rejects_non_image_content_type(client: TestClient) -> None:
    files = {"image": ("test.txt", b"hello", "text/plain")}
    r = client.post("/api/v1/predict", files=files)
    assert r.status_code == 422


def test_predict_rejects_empty_file(client: TestClient) -> None:
    files = {"image": ("test.png", b"", "image/png")}
    r = client.post("/api/v1/predict", files=files)
    assert r.status_code == 422


def test_predict_cache_hit(client: TestClient) -> None:
    data = _make_png_bytes()
    files1 = {"image": ("test.png", data, "image/png")}
    files2 = {"image": ("test.png", data, "image/png")}
    r1 = client.post("/api/v1/predict", files=files1)
    r2 = client.post("/api/v1/predict", files=files2)
    assert r1.status_code == 200 and r2.status_code == 200
    assert r2.json()["cached"] is True


def test_reset_cache(client: TestClient) -> None:
    r = client.post("/api/v1/predict/reset-cache")
    assert r.status_code == 204
