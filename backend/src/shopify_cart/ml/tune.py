"""
Optuna hyperparameter tuning for the category classifier.

Each trial:
  1. Samples hyperparameters (LR, batch size, optimizer, augmentation).
  2. Runs a short training (default 3 epochs).
  3. Logs everything as a nested MLflow run under the same experiment.
  4. Reports validation accuracy as the objective.

After N trials:
  - Best trial's model is registered in MLflow Model Registry.
  - Registered model name: settings.mlflow_registered_model_name

Parent run also logs summary artifacts:
  - summary/study_summary.json     (best params, best value, trial number)
  - summary/trials_history.json    (all trials' params + metrics)
  - best_model/                    (copy of best trial's model artifacts)

Run:
    python -m shopify_cart.ml.tune
    python -m shopify_cart.ml.tune --n-trials 15 --epochs-per-trial 3
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import mlflow
import mlflow.artifacts
import mlflow.pytorch
import numpy as np
import optuna
import torch
import torch.nn as nn
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from torch import Tensor
from torch.amp import GradScaler, autocast  # type: ignore[attr-defined,unused-ignore]
from torch.utils.data import DataLoader

from shopify_cart.config import Settings, get_settings
from shopify_cart.logging_config import configure_logging, get_logger
from shopify_cart.ml.dataset import load_splits
from shopify_cart.ml.train import (
    AugmentedSubset,
    build_model,
    freeze_backbone,
    set_seed,
    unfreeze_layer4,
)

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Tuning config
# ----------------------------------------------------------------------
@dataclass
class TuneConfig:
    data_dir: str = "data/processed"
    n_trials: int = 10
    epochs_per_trial: int = 3
    seed: int = 42
    study_name: str = "shopify-category-tuning"
    timeout_seconds: int | None = None  # None = no timeout


# ----------------------------------------------------------------------
# Single training run for a trial (short, returns val_acc)
# ----------------------------------------------------------------------
def _train_one_trial(
    *,
    model: nn.Module,
    train_loader: DataLoader[tuple[Tensor, int]],
    val_loader: DataLoader[tuple[Tensor, int]],
    optimizer: torch.optim.Optimizer,
    scheduler: torch.optim.lr_scheduler.LRScheduler,
    criterion: nn.Module,
    device: torch.device,
    use_amp: bool,
    epochs: int,
    freeze_epochs: int,
    trial: optuna.Trial,
) -> float:
    scaler = GradScaler("cuda", enabled=use_amp)
    best_val_acc = 0.0

    for epoch in range(1, epochs + 1):
        if epoch == freeze_epochs + 1:
            unfreeze_layer4(model)

        # -------- Train --------
        model.train()
        for images, labels in train_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)

            if use_amp:
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

        # -------- Validate --------
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images = images.to(device, non_blocking=True)
                labels = labels.to(device, non_blocking=True)
                logits = model(images)
                preds = logits.argmax(dim=1)
                correct += int((preds == labels).sum().item())
                total += int(labels.size(0))

        val_acc = correct / max(total, 1)
        best_val_acc = max(best_val_acc, val_acc)
        scheduler.step()

        # Report to Optuna (its own pruning logic)
        trial.report(val_acc, epoch)
        if trial.should_prune():
            logger.info("trial_pruned", epoch=epoch, val_acc=round(val_acc, 4))
            raise optuna.TrialPruned()

        # Log to currently active MLflow run (the trial's nested run)
        mlflow.log_metric("val_acc", val_acc, step=epoch)

        logger.info(
            "trial_epoch_done",
            trial=trial.number,
            epoch=epoch,
            val_acc=round(val_acc, 4),
        )

    return best_val_acc


# ----------------------------------------------------------------------
# Objective builder
# ----------------------------------------------------------------------
def _build_objective(cfg: TuneConfig) -> Any:
    data_dir = Path(cfg.data_dir)

    train_ds, val_ds, _test_ds, class_names = load_splits(data_dir)
    num_classes = len(class_names)
    logger.info(
        "tune_data_loaded",
        train=len(train_ds),
        val=len(val_ds),
        num_classes=num_classes,
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"

    def objective(trial: optuna.Trial) -> float:
        # ---- Sample hyperparameters ----
        lr_head = trial.suggest_float("lr_head", 1e-4, 5e-3, log=True)
        lr_backbone = trial.suggest_float("lr_backbone", 1e-5, 5e-4, log=True)
        weight_decay = trial.suggest_float("weight_decay", 1e-6, 1e-2, log=True)
        batch_size = trial.suggest_categorical("batch_size", [16, 32, 64])
        optimizer_name = trial.suggest_categorical("optimizer", ["adamw", "sgd"])
        augment = trial.suggest_categorical("augment", [True, False])
        freeze_epochs = trial.suggest_int("freeze_epochs", 0, max(cfg.epochs_per_trial - 1, 0))

        params = {
            "lr_head": lr_head,
            "lr_backbone": lr_backbone,
            "weight_decay": weight_decay,
            "batch_size": batch_size,
            "optimizer": optimizer_name,
            "augment": augment,
            "freeze_epochs": freeze_epochs,
        }
        logger.info("trial_start", trial=trial.number, params=params)

        set_seed(cfg.seed + trial.number)

        # ---- Data loaders ----
        train_wrapped = AugmentedSubset(train_ds, augment=bool(augment))
        val_wrapped = AugmentedSubset(val_ds, augment=False)
        train_loader: DataLoader[tuple[Tensor, int]] = DataLoader(
            train_wrapped,
            batch_size=int(batch_size),
            shuffle=True,
            num_workers=0,
            pin_memory=(device.type == "cuda"),
            drop_last=True,
        )
        val_loader: DataLoader[tuple[Tensor, int]] = DataLoader(
            val_wrapped,
            batch_size=int(batch_size),
            shuffle=False,
            num_workers=0,
            pin_memory=(device.type == "cuda"),
        )

        # ---- Model ----
        model = build_model(num_classes).to(device)
        if freeze_epochs > 0:
            freeze_backbone(model)

        fc_layer = cast(nn.Linear, getattr(model, "fc"))  # noqa: B009
        head_params: list[nn.Parameter] = list(fc_layer.parameters())
        backbone_params: list[nn.Parameter] = [
            p for n, p in model.named_parameters() if not n.startswith("fc.")
        ]

        if optimizer_name == "adamw":
            optimizer: torch.optim.Optimizer = torch.optim.AdamW(
                [
                    {"params": head_params, "lr": lr_head},
                    {
                        "params": [p for p in backbone_params if p.requires_grad],
                        "lr": lr_backbone,
                    },
                ],
                weight_decay=weight_decay,
            )
        else:  # sgd
            optimizer = torch.optim.SGD(
                [
                    {"params": head_params, "lr": lr_head},
                    {
                        "params": [p for p in backbone_params if p.requires_grad],
                        "lr": lr_backbone,
                    },
                ],
                momentum=0.9,
                weight_decay=weight_decay,
            )

        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=cfg.epochs_per_trial
        )
        criterion = nn.CrossEntropyLoss()

        # ---- MLflow nested run (one per trial) ----
        # We handle MLflow logging manually (no MLflowCallback) so we have
        # full control and can capture the run_id inside the trial.
        with mlflow.start_run(run_name=f"trial-{trial.number}", nested=True) as trial_run:
            trial.set_user_attr("mlflow_run_id", trial_run.info.run_id)

            mlflow.log_params(params)
            mlflow.set_tags(
                {
                    "trial_number": trial.number,
                    "study": cfg.study_name,
                }
            )

            mlflow.log_dict({"classes": class_names}, "class_labels.json")

            try:
                best_val_acc = _train_one_trial(
                    model=model,
                    train_loader=train_loader,
                    val_loader=val_loader,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    criterion=criterion,
                    device=device,
                    use_amp=use_amp,
                    epochs=cfg.epochs_per_trial,
                    freeze_epochs=int(freeze_epochs),
                    trial=trial,
                )
            except optuna.TrialPruned:
                mlflow.set_tag("status", "pruned")
                raise

            mlflow.log_metric("best_val_acc", best_val_acc)

            # Save model per trial (signature-based, avoids MLflow 2.17
            # input_example dtype-promotion bug).
            try:
                from mlflow.models.signature import infer_signature

                model.eval()
                sample = torch.randn(1, 3, 224, 224, dtype=torch.float32).to(device)
                with torch.no_grad():
                    sample_out = model(sample)
                signature = infer_signature(
                    sample.detach().cpu().numpy().astype(np.float32),
                    sample_out.detach().cpu().numpy().astype(np.float32),
                )
                model.train()

                mlflow.pytorch.log_model(
                    pytorch_model=model,
                    artifact_path="model",
                    signature=signature,
                )
            except Exception:
                logger.exception("trial_model_log_failed")

            logger.info(
                "trial_done",
                trial=trial.number,
                best_val_acc=round(best_val_acc, 4),
            )
            return float(best_val_acc)

    return objective


# ----------------------------------------------------------------------
# Register best trial's model
# ----------------------------------------------------------------------
def _register_best_model(
    study: optuna.Study,
    *,
    settings: Settings,
) -> str:
    """Register the best trial's logged PyTorch model in MLflow Model Registry."""
    best_trial = study.best_trial
    run_id = best_trial.user_attrs.get("mlflow_run_id")

    if not run_id:
        raise RuntimeError(
            "Best trial has no 'mlflow_run_id' user attribute. "
            "This means the trial run was not properly tracked."
        )

    model_uri = f"runs:/{run_id}/model"
    registered_name = settings.mlflow_registered_model_name

    try:
        result = mlflow.register_model(
            model_uri=model_uri,
            name=registered_name,
            tags={"stage": "tuning-best", "study": study.study_name},
        )
        logger.info(
            "model_registered",
            name=registered_name,
            version=result.version,
            run_id=run_id,
        )
        return str(result.version)
    except Exception:
        logger.exception("model_registry_failed")
        raise


# ----------------------------------------------------------------------
# Parent-run summary artifact helpers
# ----------------------------------------------------------------------
def _log_study_summary_artifact(
    study: optuna.Study,
    cfg: TuneConfig,
    *,
    best_value: float,
    best_params: dict[str, Any],
    best_trial_number: int,
) -> None:
    """Write study_summary.json and log it to the parent run."""
    study_dir = Path(cfg.data_dir) / "tuning"
    study_dir.mkdir(parents=True, exist_ok=True)

    summary_path = study_dir / "study_summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "study_name": cfg.study_name,
                "n_trials": len(study.trials),
                "n_complete": sum(1 for t in study.trials if t.state.name == "COMPLETE"),
                "n_pruned": sum(1 for t in study.trials if t.state.name == "PRUNED"),
                "best_value": best_value,
                "best_params": best_params,
                "best_trial_number": best_trial_number,
                "epochs_per_trial": cfg.epochs_per_trial,
                "seed": cfg.seed,
            },
            f,
            indent=2,
        )
    mlflow.log_artifact(str(summary_path), artifact_path="summary")
    logger.info("tuning_summary_logged", path=str(summary_path))


def _log_trials_history_artifact(study: optuna.Study, cfg: TuneConfig) -> None:
    """Write trials_history.json and log it to the parent run."""
    study_dir = Path(cfg.data_dir) / "tuning"
    study_dir.mkdir(parents=True, exist_ok=True)

    trials_history: list[dict[str, Any]] = []
    for t in study.trials:
        trials_history.append(
            {
                "number": t.number,
                "state": t.state.name,
                "value": t.value,
                "params": dict(t.params),
                "datetime_start": (t.datetime_start.isoformat() if t.datetime_start else None),
                "datetime_complete": (
                    t.datetime_complete.isoformat() if t.datetime_complete else None
                ),
            }
        )

    trials_path = study_dir / "trials_history.json"
    with trials_path.open("w", encoding="utf-8") as f:
        json.dump(trials_history, f, indent=2)
    mlflow.log_artifact(str(trials_path), artifact_path="summary")
    logger.info("tuning_trials_history_logged", path=str(trials_path))


def _log_best_model_artifact(study: optuna.Study, cfg: TuneConfig) -> None:
    """Copy the best trial's logged model into the parent run as best_model/."""
    best_run_id = study.best_trial.user_attrs.get("mlflow_run_id")
    if not best_run_id:
        logger.warning("tune_best_model_artifact_skipped", reason="no best run_id")
        return

    study_dir = Path(cfg.data_dir) / "tuning" / "best_model_download"
    study_dir.mkdir(parents=True, exist_ok=True)

    try:
        downloaded = mlflow.artifacts.download_artifacts(
            run_id=best_run_id,
            artifact_path="model",
            dst_path=str(study_dir),
        )
        mlflow.log_artifacts(downloaded, artifact_path="best_model")
        logger.info(
            "tune_best_model_artifact_logged",
            source_run=best_run_id,
            path=downloaded,
        )
    except Exception:
        logger.exception("tune_best_model_artifact_failed")


# ----------------------------------------------------------------------
# Main tuning routine
# ----------------------------------------------------------------------
def tune(cfg: TuneConfig) -> dict[str, Any]:
    settings = get_settings()
    configure_logging(
        debug=settings.app_debug,
        json_logs=settings.is_production,
    )
    set_seed(cfg.seed)

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment_name)

    # ---- Optuna study ----
    sampler = TPESampler(seed=cfg.seed, multivariate=True, group=True)
    pruner = MedianPruner(n_startup_trials=2, n_warmup_steps=1)

    study = optuna.create_study(
        study_name=cfg.study_name,
        direction="maximize",
        sampler=sampler,
        pruner=pruner,
        load_if_exists=True,
    )

    objective = _build_objective(cfg)

    # ---- MLflow parent run wrapping the whole study ----
    with mlflow.start_run(run_name=f"optuna-{cfg.study_name}") as parent_run:
        mlflow.set_tags(
            {
                "study_name": cfg.study_name,
                "n_trials": cfg.n_trials,
                "epochs_per_trial": cfg.epochs_per_trial,
                "sampler": "TPESampler",
                "pruner": "MedianPruner",
            }
        )
        study.set_user_attr("parent_run_id", parent_run.info.run_id)

        study.optimize(
            objective,
            n_trials=cfg.n_trials,
            timeout=cfg.timeout_seconds,
            show_progress_bar=True,
        )

        best_value = float(study.best_value)
        best_params = study.best_params
        best_trial_number = study.best_trial.number

        mlflow.log_metric("study_best_val_acc", best_value)
        mlflow.log_params({f"best_{k}": v for k, v in best_params.items()})
        mlflow.set_tag("best_trial_number", str(best_trial_number))

        logger.info(
            "tuning_complete",
            best_value=round(best_value, 4),
            best_trial=best_trial_number,
            best_params=best_params,
        )

        # ---- Log summary artifacts to parent run ----
        _log_study_summary_artifact(
            study,
            cfg,
            best_value=best_value,
            best_params=best_params,
            best_trial_number=best_trial_number,
        )
        _log_trials_history_artifact(study, cfg)
        _log_best_model_artifact(study, cfg)

        # ---- Register best model ----
        registered_version = ""
        try:
            registered_version = _register_best_model(study, settings=settings)
            mlflow.set_tag("registered_version", registered_version)
        except RuntimeError as exc:
            logger.error("register_best_model_skipped", error=str(exc))

        parent_run_id = parent_run.info.run_id

    return {
        "study_name": cfg.study_name,
        "n_trials": len(study.trials),
        "best_value": float(study.best_value),
        "best_params": study.best_params,
        "best_trial_number": study.best_trial.number,
        "registered_version": registered_version,
        "parent_run_id": parent_run_id,
    }


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> TuneConfig:
    p = argparse.ArgumentParser(description="Optuna hyperparameter tuning.")
    p.add_argument("--data-dir", default="data/processed")
    p.add_argument("--n-trials", type=int, default=10)
    p.add_argument("--epochs-per-trial", type=int, default=3)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--study-name", default="shopify-category-tuning")
    p.add_argument("--timeout", type=int, default=None, help="Overall timeout in seconds")
    args = p.parse_args(argv)

    return TuneConfig(
        data_dir=args.data_dir,
        n_trials=args.n_trials,
        epochs_per_trial=args.epochs_per_trial,
        seed=args.seed,
        study_name=args.study_name,
        timeout_seconds=args.timeout,
    )


def main(argv: list[str] | None = None) -> int:
    cfg = _parse_args(argv)
    result = tune(cfg)

    print("\n=== Tuning complete ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
