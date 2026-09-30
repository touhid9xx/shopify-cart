"""Verify the predictor returns real class names, not class_N fallbacks."""

from __future__ import annotations

import glob

from shopify_cart.ml.predict import CategoryPredictor


def main() -> int:
    predictor = CategoryPredictor()
    try:
        predictor.load()
    except Exception as exc:
        print(f"Load failed: {type(exc).__name__}: {exc}")
        return 1

    print("=" * 60)
    print(f"Predictor loaded: {predictor.is_loaded}")
    print(f"Device: {predictor.device}")
    print(f"Classes ({len(predictor.classes)}): {predictor.classes}")
    print("=" * 60)

    # Try a real image
    imgs = glob.glob("data/processed/test/*/*.jpg")[:1]
    if not imgs:
        print("No test images found")
        return 2

    with open(imgs[0], "rb") as f:
        img_bytes = f.read()

    result = predictor.predict(img_bytes, top_k=3)

    print()
    print(f"Prediction: {result.category}  (confidence={result.confidence:.4f})")
    print("Top-K:")
    for item in result.top_k:
        print(f"  {item.category}: {item.confidence:.4f}")
    print()
    print(f"Model: {result.model_name}  version={result.model_version}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
