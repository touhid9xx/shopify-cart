"""Verify the predictor returns real class names, not class_N fallbacks.

Run from backend/:
    python scripts/test_predictor_labels.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from shopify_cart.config import get_settings
from shopify_cart.ml.predict import CategoryPredictor


# ─── Helpers ─────────────────────────────────────────────────────────
def find_test_image() -> Path | None:
    """Return the first image we can find, trying several locations."""
    candidates = [
        "data/processed/test",
        "data/processed/val",
        "data/uploads",
    ]
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    for base in candidates:
        base_path = Path(base)
        if not base_path.is_dir():
            continue
        for ext in extensions:
            matches = sorted(base_path.rglob(ext))
            if matches:
                return matches[0]
    return None


def fail(msg: str, code: int = 1) -> int:
    print(f"\n✗ FAIL: {msg}", file=sys.stderr)
    return code


# ─── Main ────────────────────────────────────────────────────────────
def main() -> int:
    # ── Settings sanity check ──
    settings = get_settings()
    print("─" * 60)
    print("Settings")
    print("─" * 60)
    print(f"  tracking_uri:   {settings.mlflow_tracking_uri}")
    print(f"  experiment:     {settings.mlflow_experiment_name}")
    print(f"  registered:     {settings.mlflow_registered_model_name}")
    print(f"  stage:          {settings.model_stage}")
    print(f"  ml_enabled:     {settings.ml_enabled}")

    if not settings.mlflow_registered_model_name:
        return fail(
            "mlflow_registered_model_name is empty — check .env "
            "(MLFLOW_REGISTERED_MODEL_NAME) and CWD (should be backend/)."
        )

    if not settings.ml_enabled:
        return fail("ml_enabled is False — set ML_ENABLED=true in .env to test.")

    # ── Load ──
    print("\n" + "─" * 60)
    print("Loading predictor")
    print("─" * 60)
    predictor = CategoryPredictor()
    try:
        predictor.load()
    except Exception as exc:
        return fail(f"{type(exc).__name__}: {exc}")

    # ── Class labels sanity check ──
    classes = predictor.classes
    print(f"\nPredictor loaded: {predictor.is_loaded}")
    print(f"Device:           {predictor.device}")
    print(f"Classes ({len(classes)}): {classes}")

    if not predictor.is_loaded:
        return fail("predictor.is_loaded is False after load().")

    if len(classes) == 0:
        return fail(
            "Predictor loaded with 0 classes — the checkpoint and "
            "class_labels.json both lack labels. Predictions would "
            "fall back to 'class_0', 'class_1', ..."
        )

    suspicious = [c for c in classes if c.startswith("class_")]
    if suspicious:
        return fail(
            f"Class labels contain fallback names: {suspicious}. "
            "The real labels were not loaded from the run's class_labels.json."
        )

    # ── Find a test image ──
    img_path = find_test_image()
    if img_path is None:
        return fail(
            "No test image found. Looked under data/processed/{test,val} "
            "and data/uploads for jpg/jpeg/png/webp."
        )

    print(f"\nTest image: {img_path}")
    img_bytes = img_path.read_bytes()

    # ── Predict ──
    try:
        result = predictor.predict(img_bytes, top_k=3)
    except Exception as exc:
        return fail(f"predict() raised {type(exc).__name__}: {exc}")

    print()
    print("─" * 60)
    print("Prediction")
    print("─" * 60)
    print(f"  category:   {result.category}")
    print(f"  confidence: {result.confidence:.4f}")
    print(f"  top_k:")
    for item in result.top_k:
        print(f"    {item.category:24s} {item.confidence:.4f}")
    print(f"  model:      {result.model_name} v{result.model_version} "
          f"(stage={result.model_stage})")
    print(f"  cached:     {result.cached}")
    print(f"  inference:  {result.inference_ms} ms")

    # ── Final assertion: top-1 must be a real label ──
    if result.category.startswith("class_"):
        return fail(
            f"Predicted category {result.category!r} is a fallback label. "
            "Something is wrong with class loading."
        )

    print("\n✓ PASS: predictor returned real class labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
