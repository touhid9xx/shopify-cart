"""NVIDIA Shopify product catalogue — download, explore, and PyTorch Dataset.

Dataset: nvidia/Shopify-product-catalogue-8k (Apache-2.0, public).
Requires HF_TOKEN in .env for faster authenticated downloads.

Usage:
    python -m shopify_cart.ml.dataset --explore
    python -m shopify_cart.ml.dataset --download --max-per-class 500

After preprocessing (see preprocess.py), use load_splits() to obtain
PyTorch-ready splits from data/processed/.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
from PIL import Image
from torch import Tensor
from torch.utils.data import Dataset

from shopify_cart.config import get_settings
from shopify_cart.logging_config import configure_logging, get_logger

logger = get_logger(__name__)

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
# ashraq/fashion-product-images-small — 44k images, 7 master categories.
# Columns: id, gender, masterCategory, subCategory, articleType,
#          baseColour, season, year, usage, productDisplayName, image
DATASET_ID = "ashraq/fashion-product-images-small"

# ImageNet normalization constants (matches pretrained ResNet/EfficientNet)
IMAGENET_MEAN: tuple[float, float, float] = (0.485, 0.456, 0.406)
IMAGENET_STD: tuple[float, float, float] = (0.229, 0.224, 0.225)

IMAGE_SIZE = 224
CLASS_MAP_FILE = "class_map.json"

# Column names in the HF dataset
COL_IMAGE = "image"
COL_CATEGORY = "masterCategory"
COL_TITLE = "productDisplayName"


# ----------------------------------------------------------------------
# HF authentication
# ----------------------------------------------------------------------
def _ensure_hf_auth() -> None:
    """Expose HF_TOKEN to huggingface_hub via environment variable.

    huggingface_hub (>= 0.20) auto-detects HF_TOKEN from the environment,
    so no explicit login() call is required. We also set the legacy
    HUGGING_FACE_HUB_TOKEN name for older library versions.
    """
    import os

    settings = get_settings()
    if not settings.hf_token:
        logger.warning(
            "hf_login_skipped",
            reason="HF_TOKEN not set — using anonymous access (slower, rate-limited)",
        )
        return

    os.environ["HF_TOKEN"] = settings.hf_token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = settings.hf_token
    logger.info("hf_token_set_in_env", token_prefix=settings.hf_token[:7] + "…")


# ----------------------------------------------------------------------
# Load dataset from HF Hub
# ----------------------------------------------------------------------
def load_hf_dataset() -> Any:
    """Return the HF dataset split 'train' with lazy image decoding."""
    from datasets import load_dataset

    _ensure_hf_auth()
    logger.info("hf_load_start", dataset_id=DATASET_ID)
    ds = load_dataset(DATASET_ID, split="train")
    logger.info("hf_load_done", rows=len(ds), columns=ds.column_names)
    return ds


# ----------------------------------------------------------------------
# Explore: class distribution + sample images
# ----------------------------------------------------------------------
@dataclass
class ClassStats:
    """Per-class counts and total."""

    counts: dict[str, int]
    total: int

    @property
    def sorted_counts(self) -> list[tuple[str, int]]:
        return sorted(self.counts.items(), key=lambda kv: kv[1], reverse=True)


def explore_dataset(ds: Any, output_dir: Path, n_samples: int = 9) -> ClassStats:
    """Compute class distribution; save sample grid + stats JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("explore_start")
    labels = ds[COL_CATEGORY]
    counts = Counter(labels)
    stats = ClassStats(counts=dict(counts), total=len(labels))

    # ---- Print a compact table to stdout + log ----
    print()
    print("=" * 60)
    print(f"  Dataset: {DATASET_ID}")
    print(f"  Total rows: {stats.total}")
    print(f"  Unique categories: {len(counts)}")
    print("=" * 60)
    print(f"  {'category':<45} {'count':>10}")
    print("-" * 60)
    for name, cnt in stats.sorted_counts:
        print(f"  {name:<45} {cnt:>10}")
    print("=" * 60)
    print()

    # ---- Save stats JSON ----
    stats_path = output_dir / "dataset_stats.json"
    with stats_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "dataset_id": DATASET_ID,
                "total": stats.total,
                "num_classes": len(counts),
                "counts": stats.counts,
            },
            f,
            indent=2,
        )
    logger.info("explore_stats_saved", path=str(stats_path))

    # ---- Save sample images grid ----
    import matplotlib

    matplotlib.use("Agg")  # headless
    import warnings

    import matplotlib.pyplot as plt

    warnings.filterwarnings("ignore", message=".*missing from font.*")

    fig, axes = plt.subplots(3, 3, figsize=(10, 10))
    for i, ax in enumerate(axes.flat):
        if i >= n_samples:
            ax.axis("off")
            continue
        row = ds[i]
        img = row[COL_IMAGE]
        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)
        ax.imshow(img)
        ax.set_title(f"{row[COL_CATEGORY]}\n({img.size[0]}x{img.size[1]})", fontsize=9)
        ax.axis("off")
    plt.tight_layout()
    samples_path = output_dir / "sample_images.png"
    plt.savefig(samples_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("explore_samples_saved", path=str(samples_path))

    return stats


# ----------------------------------------------------------------------
# PyTorch Dataset for processed data (folder-per-class)
# ----------------------------------------------------------------------
class ProductImageDataset(Dataset[tuple[Tensor, int]]):
    """Loads preprocessed .jpg images from folder-per-class layout.

    Expected layout:
        root/
          class_a/
            img_00001.jpg
            img_00002.jpg
          class_b/
            ...

    Images are already resized/normalized offline (preprocess.py). At load
    time we only convert to tensor and normalize (ImageNet stats).
    """

    def __init__(
        self,
        root: Path,
        class_to_idx: dict[str, int],
        *,
        image_size: int = IMAGE_SIZE,
    ) -> None:
        self.root = root
        self.class_to_idx = class_to_idx
        self.image_size = image_size

        # Collect (path, label) pairs
        self.samples: list[tuple[Path, int]] = []
        for class_name, label_idx in class_to_idx.items():
            class_dir = root / class_name
            if not class_dir.is_dir():
                continue
            for img_path in sorted(class_dir.glob("*.jpg")):
                self.samples.append((img_path, label_idx))
        if not self.samples:
            raise FileNotFoundError(f"No images found under {root}. Did you run preprocess.py?")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[Tensor, int]:
        import numpy as np

        path, label = self.samples[idx]
        with Image.open(path) as im_raw:
            im: Image.Image = im_raw.convert("RGB")
            arr = torch.from_numpy(np.array(im, dtype="uint8")).permute(2, 0, 1).float() / 255.0

        # Normalize with ImageNet stats
        mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        std = torch.tensor(IMAGENET_STD).view(3, 1, 1)
        arr = (arr - mean) / std
        return arr, label


# ----------------------------------------------------------------------
# Split loader
# ----------------------------------------------------------------------
def load_splits(
    data_dir: Path | str = "data/processed",
    *,
    image_size: int = IMAGE_SIZE,
) -> tuple[
    ProductImageDataset,
    ProductImageDataset,
    ProductImageDataset,
    list[str],
]:
    """Load train/val/test ProductImageDataset from preprocessed data.

    Reads class_map.json (produced by preprocess.py) for the canonical
    class ordering. Returns (train_ds, val_ds, test_ds, class_names).
    """
    data_dir = Path(data_dir)
    class_map_path = data_dir / CLASS_MAP_FILE
    if not class_map_path.exists():
        raise FileNotFoundError(
            f"Missing {class_map_path}. Run preprocess.py first:\n"
            f"  python -m shopify_cart.ml.preprocess --source data/raw/shopify"
        )

    with class_map_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    class_to_idx: dict[str, int] = payload["class_to_idx"]
    class_names: list[str] = payload["class_names"]

    train_ds = ProductImageDataset(data_dir / "train", class_to_idx, image_size=image_size)
    val_ds = ProductImageDataset(data_dir / "val", class_to_idx, image_size=image_size)
    test_ds = ProductImageDataset(data_dir / "test", class_to_idx, image_size=image_size)
    logger.info(
        "splits_loaded_from_disk",
        train=len(train_ds),
        val=len(val_ds),
        test=len(test_ds),
        num_classes=len(class_names),
    )
    return train_ds, val_ds, test_ds, class_names


# ----------------------------------------------------------------------
# Download helper: save raw images to disk for later preprocess
# ----------------------------------------------------------------------
def download_to_disk(
    ds: Any,
    out_dir: Path,
    *,
    max_per_class: int | None = None,
    min_per_class: int = 20,
) -> dict[str, int]:
    """Save raw images to out_dir/<category>/<idx>.jpg.

    - If max_per_class is not None, only the first N images per class are kept.
    - Classes with fewer than min_per_class total images are skipped entirely
      (they would not be learnable and would hurt macro metrics).
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    # Count all classes first
    counts = Counter(ds[COL_CATEGORY])

    # Which classes survive
    kept_classes = {c for c, n in counts.items() if n >= min_per_class}
    dropped = set(counts) - kept_classes
    if dropped:
        logger.info(
            "download_skipping_small_classes",
            kept=len(kept_classes),
            dropped=len(dropped),
            dropped_names=sorted(dropped)[:20],
        )

    # Save images
    saved: Counter[str] = Counter()
    skipped_no_class = 0
    for i, row in enumerate(ds):
        cat = row[COL_CATEGORY]
        if cat not in kept_classes:
            continue
        if max_per_class is not None and saved[cat] >= max_per_class:
            continue

        img = row[COL_IMAGE]
        if not isinstance(img, Image.Image):
            img = Image.fromarray(img)
        img = img.convert("RGB")

        class_dir = out_dir / _safe_name(cat)
        class_dir.mkdir(parents=True, exist_ok=True)
        path = class_dir / f"{saved[cat]:06d}.jpg"
        img.save(path, format="JPEG", quality=92)
        saved[cat] += 1

        if (i + 1) % 500 == 0:
            logger.info("download_progress", processed=i + 1, total=len(ds))

        if max_per_class is not None and all(saved[c] >= max_per_class for c in kept_classes):
            logger.info("download_max_per_class_reached")
            break

    logger.info(
        "download_done",
        classes_saved=len(saved),
        total_images=sum(saved.values()),
        skipped_no_class=skipped_no_class,
    )
    return dict(saved)


def _safe_name(name: str) -> str:
    """Make a filesystem-safe folder name from a class label."""
    keep = "".join(c if c.isalnum() or c in "-_." else "_" for c in name)
    return keep.strip("._") or "unknown"


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NVIDIA Shopify dataset tools.")
    p.add_argument("--explore", action="store_true", help="Print class distribution.")
    p.add_argument(
        "--download",
        action="store_true",
        help="Download and save raw images to disk.",
    )
    p.add_argument(
        "--max-per-class",
        type=int,
        default=None,
        help="Cap images per class (None = all).",
    )
    p.add_argument(
        "--min-per-class",
        type=int,
        default=20,
        help="Skip classes with fewer than this many images (default 20).",
    )
    p.add_argument(
        "--raw-dir",
        type=Path,
        default=Path("data/raw/shopify"),
        help="Where to save raw images.",
    )
    p.add_argument(
        "--explore-dir",
        type=Path,
        default=Path("data/raw/_explore"),
        help="Where to save explore artifacts.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    cfg = _parse_args(argv)
    settings = get_settings()
    configure_logging(debug=settings.app_debug)

    if not cfg.explore and not cfg.download:
        print("Nothing to do. Pass --explore and/or --download.")
        return 1

    ds = load_hf_dataset()

    if cfg.explore:
        explore_dataset(ds, cfg.explore_dir)

    if cfg.download:
        saved = download_to_disk(
            ds,
            cfg.raw_dir,
            max_per_class=cfg.max_per_class,
            min_per_class=cfg.min_per_class,
        )
        print()
        print("=" * 60)
        print(f"  Saved {sum(saved.values())} images across {len(saved)} classes")
        print(f"  Raw dir: {cfg.raw_dir.resolve()}")
        print("=" * 60)
        print()
        print("  Next: run preprocess.py to resize + split")
        print("        python -m shopify_cart.ml.preprocess")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
