"""
Training pipeline for the product category classifier.

GTX 1060 (6 GB VRAM) constraints:
  - ResNet-18 (11 M params, ~45 MB in fp32)
  - batch_size=32 with AMP (mixed precision) → fits in ~3.5 GB
  - Freeze backbone first, then optional fine-tune of layer4

MLflow:
  - Experiment: MODEL_NAME (default 'shopify-category-classifier')
  - Logs: params, per-epoch metrics, confusion matrix, training history
  - Model artifact: state_dict in `pytorch_model/` (version-agnostic,
    avoids `mlflow.pytorch.pickle_module` cross-version issues)

Run:
    python -m shopify_cart.ml.train
    python -m shopify_cart.ml.train --epochs 10 --batch-size 32 --fine-tune
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import mlflow
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import confusion_matrix, f1_score
from torch import Tensor
from torch.amp import GradScaler, autocast  # type: ignore[attr-defined,unused-ignore]
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import ResNet, ResNet18_Weights, resnet18

from shopify_cart.config import get_settings
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.ml.dataset import (
    IMAGENET_MEAN,
    IMAGENET_STD,
    ProductImageDataset,
    load_splits,
)

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------
@dataclass
class TrainConfig:
    data_dir: str = "data/processed"
    epochs: int = 5
    batch_size: int = 32
    lr_head: float = 1e-3
    lr_backbone: float = 1e-4
    weight_decay: float = 1e-4
    num_workers: int = 0  # Windows: 0 avoids spawn overhead
    seed: int = 42
    freeze_backbone_epochs: int = 2
    amp: bool = True
    patience: int = 3
    fine_tune: bool = False


# ----------------------------------------------------------------------
# Reproducibility
# ----------------------------------------------------------------------
def set_seed(seed: int) -> None:
    import random

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


# ----------------------------------------------------------------------
# Dataset wrapper with on-the-fly augmentation
# ----------------------------------------------------------------------
class AugmentedSubset(Dataset[tuple[Tensor, int]]):
    """Tensor-backed augmentation wrapper around ProductImageDataset."""

    def __init__(
        self,
        base: ProductImageDataset,
        augment: bool,
        image_size: int = 224,
    ) -> None:
        self.base = base
        self.augment = augment
        if augment:
            self._aug: transforms.Compose | None = transforms.Compose(
                [
                    transforms.RandomHorizontalFlip(p=0.5),
                    transforms.RandomRotation(degrees=10),
                    transforms.ColorJitter(brightness=0.15, contrast=0.15),
                ]
            )
        else:
            self._aug = None
        self._mean = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
        self._std = torch.tensor(IMAGENET_STD).view(3, 1, 1)

    def __len__(self) -> int:
        return len(self.base)

    def __getitem__(self, idx: int) -> tuple[Tensor, int]:
        img, label = self.base[idx]
        if self._aug is not None:
            img_denorm = img * self._std + self._mean
            img_denorm = torch.clamp(img_denorm, 0.0, 1.0)
            img_aug = self._aug(img_denorm)
            img = (img_aug - self._mean) / self._std
        return img, label


# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------
def build_model(num_classes: int) -> nn.Module:
    """ResNet-18 with ImageNet weights, replace the final FC."""
    weights = ResNet18_Weights.IMAGENET1K_V1
    model: ResNet = resnet18(weights=weights)
    in_features: int = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    return model


def freeze_backbone(model: nn.Module) -> None:
    for name, param in model.named_parameters():
        if not name.startswith("fc."):
            param.requires_grad = False


def unfreeze_layer4(model: nn.Module) -> None:
    for name, param in model.named_parameters():
        if name.startswith("layer4.") or name.startswith("fc."):
            param.requires_grad = True


# ----------------------------------------------------------------------
# Train / eval loops
# ----------------------------------------------------------------------
def _train_one_epoch(
    model: nn.Module,
    loader: DataLoader[tuple[Tensor, int]],
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
    scaler: GradScaler | None,
    *,
    use_amp: bool,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)

        if use_amp and scaler is not None:
            with autocast(device_type="cuda", dtype=torch.float16):
                logits = model(images)
                loss = criterion(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
        else:
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

        total_loss += float(loss.item()) * labels.size(0)
        preds = logits.argmax(dim=1)
        correct += int((preds == labels).sum().item())
        total += int(labels.size(0))

    return total_loss / max(total, 1), correct / max(total, 1)


@torch.no_grad()
def _evaluate(
    model: nn.Module,
    loader: DataLoader[tuple[Tensor, int]],
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    all_preds: list[int] = []
    all_labels: list[int] = []

    for images, labels in loader:
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)

        logits = model(images)
        loss = criterion(logits, labels)

        total_loss += float(loss.item()) * labels.size(0)
        preds = logits.argmax(dim=1)
        correct += int((preds == labels).sum().item())
        total += int(labels.size(0))

        all_preds.extend(int(x) for x in preds.cpu().tolist())
        all_labels.extend(int(x) for x in labels.cpu().tolist())

    return (
        total_loss / max(total, 1),
        correct / max(total, 1),
        np.array(all_preds),
        np.array(all_labels),
    )


# ----------------------------------------------------------------------
# Main training routine
# ----------------------------------------------------------------------
def train(cfg: TrainConfig) -> dict[str, Any]:
    settings = get_settings()
    configure_logging(
        debug=settings.app_debug,
        json_logs=settings.is_production,
    )
    set_seed(cfg.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info("training_start", device=str(device), config=vars(cfg))

    # ---- Load data ----
    data_dir = Path(cfg.data_dir)
    train_ds, val_ds, _test_ds, class_names = load_splits(data_dir)
    num_classes = len(class_names)
    logger.info(
        "splits_loaded",
        train=len(train_ds),
        val=len(val_ds),
        test=len(_test_ds),
        num_classes=num_classes,
    )

    train_wrapped = AugmentedSubset(train_ds, augment=True)
    val_wrapped = AugmentedSubset(val_ds, augment=False)

    train_loader: DataLoader[tuple[Tensor, int]] = DataLoader(
        train_wrapped,
        batch_size=cfg.batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        pin_memory=(device.type == "cuda"),
        drop_last=True,
    )
    val_loader: DataLoader[tuple[Tensor, int]] = DataLoader(
        val_wrapped,
        batch_size=cfg.batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        pin_memory=(device.type == "cuda"),
    )

    # ---- Model ----
    model = build_model(num_classes).to(device)

    if not cfg.fine_tune:
        freeze_backbone(model)
        logger.info("backbone_frozen")

    fc_layer = cast(nn.Linear, getattr(model, "fc"))  # noqa: B009
    head_params: list[nn.Parameter] = list(fc_layer.parameters())
    backbone_params: list[nn.Parameter] = [
        p for n, p in model.named_parameters() if not n.startswith("fc.")
    ]

    optimizer = torch.optim.AdamW(
        [
            {"params": head_params, "lr": cfg.lr_head},
            {
                "params": [p for p in backbone_params if p.requires_grad],
                "lr": cfg.lr_backbone,
            },
        ],
        weight_decay=cfg.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=cfg.epochs)
    criterion = nn.CrossEntropyLoss()

    use_amp = cfg.amp and device.type == "cuda"
    scaler: GradScaler | None = GradScaler("cuda") if use_amp else None

    # ---- MLflow ----
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)

    run_name = f"resnet18-bs{cfg.batch_size}-ep{cfg.epochs}-seed{cfg.seed}"
    with mlflow.start_run(run_name=run_name) as run:
        mlflow.log_params(
            {
                "model": "resnet18",
                "dataset": "ashraq/fashion-product-images-small",
                "num_classes": num_classes,
                "image_size": 224,
                "epochs": cfg.epochs,
                "batch_size": cfg.batch_size,
                "lr_head": cfg.lr_head,
                "lr_backbone": cfg.lr_backbone,
                "weight_decay": cfg.weight_decay,
                "amp": use_amp,
                "freeze_backbone_epochs": cfg.freeze_backbone_epochs,
                "seed": cfg.seed,
                "fine_tune": cfg.fine_tune,
                "device": str(device),
                "train_size": len(train_ds),
                "val_size": len(val_ds),
                "test_size": len(_test_ds),
            }
        )
        mlflow.log_dict({"classes": class_names}, "class_labels.json")

        best_val_acc = 0.0
        best_epoch = 0
        epochs_without_improve = 0
        history: list[dict[str, float]] = []

        val_preds: np.ndarray = np.array([], dtype=np.int64)
        val_labels: np.ndarray = np.array([], dtype=np.int64)

        for epoch in range(1, cfg.epochs + 1):
            if not cfg.fine_tune and epoch == cfg.freeze_backbone_epochs + 1:
                unfreeze_layer4(model)
                logger.info("layer4_unfrozen", epoch=epoch)

            train_loss, train_acc = _train_one_epoch(
                model,
                train_loader,
                optimizer,
                criterion,
                device,
                scaler,
                use_amp=use_amp,
            )
            val_loss, val_acc, val_preds, val_labels = _evaluate(
                model, val_loader, criterion, device
            )

            scheduler.step()

            val_f1 = float(f1_score(val_labels, val_preds, average="macro", zero_division=0))

            mlflow.log_metrics(
                {
                    "train_loss": train_loss,
                    "train_acc": train_acc,
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                    "val_f1_macro": val_f1,
                    "lr_head": optimizer.param_groups[0]["lr"],
                },
                step=epoch,
            )
            history.append(
                {
                    "epoch": epoch,
                    "train_loss": train_loss,
                    "train_acc": train_acc,
                    "val_loss": val_loss,
                    "val_acc": val_acc,
                    "val_f1_macro": val_f1,
                }
            )

            logger.info(
                "epoch_done",
                epoch=epoch,
                train_loss=round(train_loss, 4),
                train_acc=round(train_acc, 4),
                val_loss=round(val_loss, 4),
                val_acc=round(val_acc, 4),
                val_f1=round(val_f1, 4),
            )

            if val_acc > best_val_acc:
                best_val_acc = val_acc
                best_epoch = epoch
                epochs_without_improve = 0
                torch.save(
                    {
                        "model_state_dict": model.state_dict(),
                        "num_classes": num_classes,
                        "classes": class_names,
                        "epoch": epoch,
                        "val_acc": val_acc,
                        "architecture": "resnet18",
                    },
                    data_dir / "best_model.pt",
                )
            else:
                epochs_without_improve += 1

            if epochs_without_improve >= cfg.patience:
                logger.info("early_stopping", epoch=epoch, best_epoch=best_epoch)
                break

        # ---------- Log artifacts ----------
        mlflow.log_metric("best_val_acc", best_val_acc)
        mlflow.log_metric("best_epoch", float(best_epoch))

        # Confusion matrix
        cm = confusion_matrix(val_labels, val_preds, labels=list(range(num_classes)))
        cm_path = data_dir / "confusion_matrix.json"
        with cm_path.open("w", encoding="utf-8") as f:
            json.dump({"matrix": cm.tolist(), "classes": class_names}, f, indent=2)
        mlflow.log_artifact(str(cm_path), artifact_path="metrics")

        # Training history
        hist_path = data_dir / "training_history.json"
        with hist_path.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
        mlflow.log_artifact(str(hist_path), artifact_path="metrics")

        # ---------- Model artifact: raw state_dict (version-agnostic) ----------
        # We deliberately avoid `mlflow.pytorch.log_model()` because the
        # pickle-module reference it writes can break across PyTorch/MLflow
        # versions (e.g. +cu124 vs +cpu wheels). A raw `torch.save()` of the
        # state_dict is portable and always loadable.
        best_model_path = data_dir / "best_model.pt"
        if best_model_path.exists():
            mlflow.log_artifact(str(best_model_path), artifact_path="pytorch_model")

        run_id: str = run.info.run_id
        logger.info(
            "training_complete",
            run_id=run_id,
            best_val_acc=round(best_val_acc, 4),
            best_epoch=best_epoch,
        )

    return {
        "run_id": run_id,
        "best_val_acc": best_val_acc,
        "best_epoch": best_epoch,
        "num_classes": num_classes,
        "classes": class_names,
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> TrainConfig:
    p = argparse.ArgumentParser(description="Train the category classifier.")
    p.add_argument("--data-dir", default="data/processed")
    p.add_argument("--epochs", type=int, default=5)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr-head", type=float, default=1e-3)
    p.add_argument("--lr-backbone", type=float, default=1e-4)
    p.add_argument("--weight-decay", type=float, default=1e-4)
    p.add_argument("--patience", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--no-amp", action="store_true")
    p.add_argument("--fine-tune", action="store_true")
    args = p.parse_args(argv)

    return TrainConfig(
        data_dir=args.data_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr_head=args.lr_head,
        lr_backbone=args.lr_backbone,
        weight_decay=args.weight_decay,
        patience=args.patience,
        seed=args.seed,
        amp=not args.no_amp,
        fine_tune=args.fine_tune,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = _parse_args(argv)
    train(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
