"""Preprocess raw Shopify images into PyTorch-ready train/val/test splits.

- Reads:  data/raw/shopify/<category>/*.jpg
- Writes: data/processed/{train,val,test}/<category>/*.jpg (resized 224x224)
- Also writes: data/processed/class_map.json  (class_to_idx + class_names)
- And: data/processed/split_manifest.json     (audit trail)

Usage:
    python -m shopify_cart.ml.preprocess
    python -m shopify_cart.ml.preprocess --source data/raw/shopify --out data/processed
    python -m shopify_cart.ml.preprocess --train 0.7 --val 0.15 --test 0.15
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from shopify_cart.config import get_settings
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.ml.dataset import IMAGE_SIZE

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
DEFAULT_SOURCE = Path("data/raw/shopify")
DEFAULT_OUT = Path("data/processed")
MIN_IMAGES_PER_CLASS = 20  # classes with fewer examples are dropped


# ----------------------------------------------------------------------
# Core logic
# ----------------------------------------------------------------------
def _list_class_dirs(source: Path) -> list[Path]:
    """Return subdirectories of source that contain at least one .jpg."""
    if not source.is_dir():
        raise FileNotFoundError(f"Source dir {source} not found. Run dataset.py --download first.")
    return sorted(p for p in source.iterdir() if p.is_dir() and any(p.glob("*.jpg")))


def _split_indices(
    n: int, train: float, val: float, test: float, seed: int
) -> tuple[list[int], list[int], list[int]]:
    """Split [0..n) into three index lists proportionally."""
    assert abs(train + val + test - 1.0) < 1e-6, "splits must sum to 1.0"
    idxs = list(range(n))
    rng = random.Random(seed)
    rng.shuffle(idxs)

    n_train = int(n * train)
    n_val = int(n * val)
    train_idx = idxs[:n_train]
    val_idx = idxs[n_train : n_train + n_val]
    test_idx = idxs[n_train + n_val :]
    return train_idx, val_idx, test_idx


def _resize_and_save(src: Path, dst: Path, size: int = IMAGE_SIZE) -> None:
    """Load src, resize to (size, size), save as JPEG at dst."""
    with Image.open(src) as im_raw:
        converted: Image.Image = im_raw.convert("RGB")
        resized: Image.Image = converted.resize((size, size), Image.Resampling.BILINEAR)
        resized.save(dst, format="JPEG", quality=88)


def _reset_output(out: Path) -> None:
    """Delete old processed dir and recreate empty structure."""
    if out.exists():
        logger.warning("preprocess_removing_old_output", path=str(out))
        shutil.rmtree(out)
    (out / "train").mkdir(parents=True)
    (out / "val").mkdir(parents=True)
    (out / "test").mkdir(parents=True)


def preprocess(
    source: Path = DEFAULT_SOURCE,
    out: Path = DEFAULT_OUT,
    *,
    train: float = 0.7,
    val: float = 0.15,
    test: float = 0.15,
    seed: int = 42,
    min_per_class: int = MIN_IMAGES_PER_CLASS,
) -> dict[str, object]:
    """Run the full preprocess pipeline. Returns a summary dict."""
    class_dirs = _list_class_dirs(source)
    if not class_dirs:
        raise RuntimeError(f"No class directories found in {source}")

    logger.info("preprocess_start", num_classes=len(class_dirs), source=str(source))

    # ---- Filter small classes and build class map ----
    kept_classes: list[str] = []
    dropped: list[tuple[str, int]] = []
    for cd in class_dirs:
        n = len(list(cd.glob("*.jpg")))
        if n < min_per_class:
            dropped.append((cd.name, n))
            continue
        kept_classes.append(cd.name)

    if dropped:
        logger.info(
            "preprocess_dropping_small_classes",
            count=len(dropped),
            names=[n for n, _ in dropped],
        )

    if not kept_classes:
        raise RuntimeError("All classes were dropped by min_per_class filter.")

    # Canonical ordering by name (deterministic across runs)
    kept_classes.sort()
    class_to_idx = {name: i for i, name in enumerate(kept_classes)}
    class_names = list(kept_classes)

    # ---- Reset output dir ----
    _reset_output(out)

    # ---- Process each class ----
    totals: Counter[str] = Counter()
    manifest: dict[str, object] = {
        "source": str(source),
        "out": str(out),
        "train_frac": train,
        "val_frac": val,
        "test_frac": test,
        "seed": seed,
        "min_per_class": min_per_class,
        "dropped_classes": [{"name": n, "count": c} for n, c in dropped],
        "kept_classes": class_names,
        "per_class": {},
    }

    for class_name in kept_classes:
        class_dir = source / class_name
        files = sorted(class_dir.glob("*.jpg"))
        tr_i, va_i, te_i = _split_indices(len(files), train, val, test, seed)

        for split_name, indices in (("train", tr_i), ("val", va_i), ("test", te_i)):
            split_dir = out / split_name / class_name
            split_dir.mkdir(parents=True, exist_ok=True)
            for idx in indices:
                src_path = files[idx]
                dst_path = split_dir / src_path.name
                try:
                    _resize_and_save(src_path, dst_path)
                except (OSError, UnidentifiedImageError) as exc:
                    logger.warning(
                        "preprocess_image_failed",
                        path=str(src_path),
                        error=str(exc),
                    )
                    dst_path.unlink(missing_ok=True)

        counts = {
            "train": len(list((out / "train" / class_name).glob("*.jpg"))),
            "val": len(list((out / "val" / class_name).glob("*.jpg"))),
            "test": len(list((out / "test" / class_name).glob("*.jpg"))),
        }
        totals["train"] += counts["train"]
        totals["val"] += counts["val"]
        totals["test"] += counts["test"]
        manifest["per_class"][class_name] = counts  # type: ignore[index]

        logger.info("preprocess_class_done", class_name=class_name, **counts)

    # ---- Save class map ----
    class_map_path = out / "class_map.json"
    with class_map_path.open("w", encoding="utf-8") as f:
        json.dump(
            {"class_to_idx": class_to_idx, "class_names": class_names},
            f,
            indent=2,
        )

    # ---- Save manifest ----
    manifest["totals"] = dict(totals)
    manifest["num_classes"] = len(class_names)
    manifest_path = out / "split_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logger.info(
        "preprocess_done",
        num_classes=len(class_names),
        train=totals["train"],
        val=totals["val"],
        test=totals["test"],
        class_map=str(class_map_path),
        manifest=str(manifest_path),
    )

    # ---- Pretty print summary ----
    print()
    print("=" * 68)
    print(f"  Preprocess complete — {len(class_names)} classes")
    print("=" * 68)
    print(f"  {'class':<40} {'train':>8} {'val':>8} {'test':>8}")
    print("-" * 68)
    for name in class_names:
        c = manifest["per_class"][name]  # type: ignore[index]
        print(f"  {name:<40} {c['train']:>8} {c['val']:>8} {c['test']:>8}")
    print("-" * 68)
    print(f"  {'TOTAL':<40} {totals['train']:>8} {totals['val']:>8} {totals['test']:>8}")
    print("=" * 68)
    print()
    print(f"  Class map: {class_map_path}")
    print(f"  Manifest:  {manifest_path}")
    print()
    print("  Next: train a model")
    print("        python -m shopify_cart.ml.train --epochs 5 --batch-size 32")
    print()

    return manifest


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Preprocess raw dataset into splits.")
    p.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--train", type=float, default=0.7)
    p.add_argument("--val", type=float, default=0.15)
    p.add_argument("--test", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--min-per-class", type=int, default=MIN_IMAGES_PER_CLASS)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    cfg = _parse_args(argv)
    settings = get_settings()
    configure_logging(debug=settings.app_debug)

    preprocess(
        source=cfg.source,
        out=cfg.out,
        train=cfg.train,
        val=cfg.val,
        test=cfg.test,
        seed=cfg.seed,
        min_per_class=cfg.min_per_class,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
