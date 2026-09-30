"""
Evaluate a trained model on the test set.

Loads best_model.pt (or an MLflow-registered model), computes per-class
F1, top-1 and top-5 accuracy, and logs everything to MLflow.

Run:
    python -m shopify_cart.ml.evaluate
    python -m shopify_cart.ml.evaluate --model-path data/processed/best_model.pt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    top_k_accuracy_score,
)
from torch import Tensor
from torch.utils.data import DataLoader

from shopify_cart.config import get_settings
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.ml.dataset import load_splits
from shopify_cart.ml.train import build_model

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Evaluation
# ----------------------------------------------------------------------
@torch.no_grad()
def evaluate(
    model: nn.Module,
    loader: DataLoader[tuple[Tensor, int]],
    device: torch.device,
    num_classes: int,
    class_names: list[str],
) -> dict[str, Any]:
    """Run inference on the test loader; return metrics dict."""
    model.eval()
    all_logits: list[Tensor] = []
    all_labels: list[int] = []

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        logits = model(images)
        all_logits.append(logits.detach().cpu())
        all_labels.extend(int(x) for x in labels.tolist())

    logits_cat = torch.cat(all_logits, dim=0)  # (N, C)
    labels_arr = np.array(all_labels, dtype=np.int64)

    probs = torch.softmax(logits_cat, dim=1).numpy()
    preds = logits_cat.argmax(dim=1).numpy()

    top1 = float((preds == labels_arr).mean())

    # top-5 is only meaningful when num_classes >= 5
    top5: float
    if num_classes >= 5:
        try:
            top5 = float(
                top_k_accuracy_score(
                    labels_arr,
                    probs,
                    k=min(5, num_classes),
                    labels=list(range(num_classes)),
                )
            )
        except ValueError:
            top5 = top1
    else:
        # With <5 classes, top-5 == top-1; mark as N/A in JSON
        top5 = float("nan")

    macro_f1 = float(f1_score(labels_arr, preds, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(labels_arr, preds, average="weighted", zero_division=0))

    cm = confusion_matrix(labels_arr, preds, labels=list(range(num_classes)))

    report = classification_report(
        labels_arr,
        preds,
        labels=list(range(num_classes)),
        target_names=class_names,
        zero_division=0,
        output_dict=True,
    )

    return {
        "top1_accuracy": top1,
        "top5_accuracy": top5,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "confusion_matrix": cm.tolist(),
        "classification_report": report,
        "num_samples": len(labels_arr),
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate a trained classifier.")
    p.add_argument(
        "--model-path",
        default="data/processed/best_model.pt",
        help="Path to a .pt checkpoint produced by train.py.",
    )
    p.add_argument("--data-dir", default="data/processed")
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument(
        "--no-mlflow",
        action="store_true",
        help="Skip MLflow logging (use for offline evaluation).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    settings = get_settings()
    configure_logging(
        debug=settings.app_debug,
        json_logs=settings.is_production,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("eval_start", device=str(device))

    # ---- Load data ----
    data_dir = Path(args.data_dir)
    _train, _val, test_ds, class_names = load_splits(data_dir)
    num_classes = len(class_names)
    logger.info("test_loaded", test_size=len(test_ds), num_classes=num_classes)

    test_loader: DataLoader[tuple[Tensor, int]] = DataLoader(
        test_ds,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
        pin_memory=(device.type == "cuda"),
    )

    # ---- Load model ----
    model_path = Path(args.model_path)
    if not model_path.exists():
        logger.error("model_path_missing", path=str(model_path))
        return 2

    blob: dict[str, Any] = torch.load(model_path, weights_only=False, map_location=device)
    state = blob.get("model_state_dict", blob)
    saved_classes: list[str] = blob.get("classes", class_names)

    model = build_model(num_classes).to(device)
    model.load_state_dict(state)
    logger.info(
        "model_loaded",
        path=str(model_path),
        saved_epoch=blob.get("epoch"),
        saved_val_acc=blob.get("val_acc"),
    )

    # ---- Evaluate ----
    metrics = evaluate(model, test_loader, device, num_classes, saved_classes)
    logger.info(
        "eval_done",
        top1=round(float(metrics["top1_accuracy"]), 4),
        top5=(
            round(float(metrics["top5_accuracy"]), 4)
            if not np.isnan(float(metrics["top5_accuracy"]))
            else "n/a"
        ),
        macro_f1=round(float(metrics["macro_f1"]), 4),
    )

    # ---- Pretty print report ----
    report = metrics["classification_report"]
    assert isinstance(report, dict)
    print("\n=== Per-class report ===")
    for name, stats in report.items():
        if not isinstance(stats, dict):
            continue
        if name in {"accuracy", "macro avg", "weighted avg"}:
            continue
        print(
            f"  {name:>20}:  "
            f"precision={stats['precision']:.3f}  "
            f"recall={stats['recall']:.3f}  "
            f"f1={stats['f1-score']:.3f}  "
            f"support={int(stats['support'])}"
        )

    print("\n=== Summary ===")
    print(f"  Top-1 accuracy: {metrics['top1_accuracy']:.4f}")
    if not np.isnan(float(metrics["top5_accuracy"])):
        print(f"  Top-5 accuracy: {metrics['top5_accuracy']:.4f}")
    else:
        print(f"  Top-5 accuracy: n/a (only {num_classes} classes)")
    print(f"  Macro F1:       {metrics['macro_f1']:.4f}")
    print(f"  Weighted F1:    {metrics['weighted_f1']:.4f}")
    print(f"  Test samples:   {metrics['num_samples']}")

    # ---- Save report locally ----
    out = data_dir / "test_metrics.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(
            {
                **{k: v for k, v in metrics.items() if k != "classification_report"},
                "classes": saved_classes,
                "classification_report": report,
            },
            f,
            indent=2,
            default=str,  # handle NaN
        )
    logger.info("test_metrics_saved", path=str(out))

    # ---- Log to MLflow ----
    if not args.no_mlflow:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(settings.mlflow_experiment_name)
        with mlflow.start_run(run_name="evaluate-best-model") as run:
            mlflow.log_metrics(
                {
                    "test_top1": float(metrics["top1_accuracy"]),
                    "test_macro_f1": float(metrics["macro_f1"]),
                    "test_weighted_f1": float(metrics["weighted_f1"]),
                }
            )
            # Only log top5 if meaningful
            if not np.isnan(float(metrics["top5_accuracy"])):
                mlflow.log_metric("test_top5", float(metrics["top5_accuracy"]))

            mlflow.log_dict(
                {
                    "classes": saved_classes,
                    "confusion_matrix": metrics["confusion_matrix"],
                },
                "test_metrics.json",
            )
            mlflow.log_artifact(str(out), artifact_path="metrics")
            logger.info("mlflow_eval_logged", run_id=run.info.run_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
