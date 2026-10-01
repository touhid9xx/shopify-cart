"""
Prediction service: load model state_dict from MLflow artifacts, run inference.

Design:
  - Singleton loader (thread-safe via lock)
  - LRU cache keyed by image content hash
  - Top-K classification with confidence
  - Loads `best_model.pt` (state_dict) — NOT `mlflow.pytorch.load_model()`,
    which is fragile across torch wheel variants (+cpu vs +cu118 vs +cu124).
  - Rebuilds the ResNet-18 shell with `pretrained=False` because we load
    our own weights — no need for ImageNet download inside offline containers.
"""

from __future__ import annotations

import hashlib
import io
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, cast

import mlflow
import torch
import torch.nn as nn
from PIL import Image
from torch import Tensor
from torchvision import transforms
from torchvision.transforms import InterpolationMode

from shopify_cart.config import get_settings
from shopify_cart.exceptions import MLModelError, ValidationError
from shopify_cart.logging_config import get_logger
from shopify_cart.ml.dataset import IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD
from shopify_cart.ml.train import build_model

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Data structures
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class PredictionItem:
    category: str
    category_index: int
    confidence: float


@dataclass(frozen=True)
class PredictionResult:
    category: str
    confidence: float
    top_k: list[PredictionItem]
    model_name: str
    model_version: str | None
    model_stage: str | None
    cached: bool
    inference_ms: float


# ----------------------------------------------------------------------
# LRU cache for predictions
# ----------------------------------------------------------------------
class _LRUPredictionCache:
    """Thread-safe LRU cache for prediction results."""

    def __init__(self, max_size: int = 1024) -> None:
        self._max = max_size
        self._data: OrderedDict[str, PredictionResult] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> PredictionResult | None:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key: str, value: PredictionResult) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            while len(self._data) > self._max:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        return len(self._data)


# ----------------------------------------------------------------------
# Predictor
# ----------------------------------------------------------------------
class CategoryPredictor:
    """
    Wraps the trained model. Load once, reuse.

    Loads a raw state_dict artifact (`best_model.pt`) from the MLflow run
    that registered the model. Uses `build_model()` to reconstruct the
    ResNet-18 shell and loads weights into it.
    """

    _PREPROCESS = transforms.Compose(
        [
            transforms.Resize((IMAGE_SIZE, IMAGE_SIZE), interpolation=InterpolationMode.BILINEAR),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )

    def __init__(self, *, cache_size: int = 1024) -> None:
        self._settings = get_settings()
        self._model: nn.Module | None = None
        self._classes: list[str] = []
        self._version: str | None = None
        self._stage: str | None = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._cache = _LRUPredictionCache(max_size=cache_size)
        self._lock = threading.Lock()
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def classes(self) -> list[str]:
        return list(self._classes)

    @property
    def device(self) -> str:
        return str(self._device)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load(self) -> None:
        with self._lock:
            if self._loaded:
                return
            self._load_unlocked()

    def _load_unlocked(self) -> None:
        settings = self._settings
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

        model_name = settings.mlflow_registered_model_name
        stage = settings.model_stage

        logger.info(
            "predictor_loading",
            model_name=model_name,
            stage=stage,
            tracking_uri=settings.mlflow_tracking_uri,
            device=str(self._device),
        )

        # ---- Resolve version + run_id ----
        try:
            from mlflow.tracking import MlflowClient

            client = MlflowClient()

            all_versions = client.search_model_versions(f"name='{model_name}'")
            if not all_versions:
                raise MLModelError(f"No model version found for {model_name!r}.")

            versions_sorted = sorted(all_versions, key=lambda v: int(v.version), reverse=True)

            chosen = None
            if stage and stage.lower() not in {"none", ""}:
                for v in versions_sorted:
                    if (v.current_stage or "").lower() == stage.lower():
                        chosen = v
                        break

            if chosen is None:
                chosen = versions_sorted[0]

            version = chosen.version
            run_id = chosen.run_id
            stage_used = chosen.current_stage

            if not run_id:
                raise MLModelError(f"Model version {version} has no run_id.")

            logger.info(
                "predictor_resolved_version",
                version=version,
                run_id=run_id,
                stage=stage_used,
            )
        except MLModelError:
            raise
        except Exception as exc:
            raise MLModelError(f"Cannot access MLflow registry for {model_name!r}: {exc}") from exc

        # ---- Download state_dict artifact ----
        # Look for pytorch_model/best_model.pt first (our convention);
        # fall back to pytorch_model/model.pth (older MLflow log_model output).
        try:
            from mlflow.artifacts import download_artifacts

            candidates = [
                "pytorch_model/best_model.pt",
                "pytorch_model/model_state.pt",
                "pytorch_model/data/model.pth",
                "model/best_model.pt",
            ]
            state_path: str | None = None
            last_exc: Exception | None = None
            for rel in candidates:
                try:
                    state_path = download_artifacts(run_id=run_id, artifact_path=rel)
                    logger.info("predictor_state_loaded", path=rel)
                    break
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    continue

            if state_path is None:
                raise MLModelError(
                    f"Could not find a state_dict artifact in run {run_id}. "
                    f"Tried: {candidates}. Last error: {last_exc}"
                )
        except MLModelError:
            raise
        except Exception as exc:
            raise MLModelError(f"Failed to download state_dict from run {run_id}: {exc}") from exc

        # ---- Load state_dict (works on any torch wheel — cpu/cu118/cu124) ----
        try:
            # weights_only=False is required because our checkpoint is a
            # plain dict of {model_state_dict, num_classes, classes, ...}.
            blob: dict[str, Any] = torch.load(
                state_path, map_location=self._device, weights_only=False
            )
        except Exception as exc:
            raise MLModelError(f"Failed to torch.load {state_path}: {exc}") from exc

        # Handle two possible shapes:
        #   1. {'model_state_dict': ..., 'num_classes': ..., 'classes': ...}
        #   2. raw state_dict (OrderedDict) — fall back to fetch classes from run
        if isinstance(blob, dict) and "model_state_dict" in blob:
            state_dict = blob["model_state_dict"]
            num_classes = int(blob.get("num_classes", 0)) or None
            classes = list(blob.get("classes", []))
        else:
            state_dict = blob
            num_classes = None
            classes = []

        if num_classes is None:
            # Infer from final FC weight shape
            fc_weight = state_dict.get("fc.weight")
            if fc_weight is None:
                raise MLModelError("state_dict missing 'fc.weight'; cannot infer classes.")
            num_classes = int(fc_weight.shape[0])

        if not classes:
            classes = self._load_classes_from_run(run_id)

        # ---- Build model + load weights ----
        # pretrained=False: we load our own state_dict, so fetching
        # ImageNet weights is unnecessary AND fails in offline containers
        # (the app container has no outbound internet access to
        # download.pytorch.org).
        try:
            model: nn.Module = build_model(num_classes, pretrained=False)
            model.load_state_dict(state_dict)
            model.eval()
            model.to(self._device)
        except Exception as exc:
            raise MLModelError(f"Failed to rebuild model from state_dict: {exc}") from exc

        self._model = model
        self._classes = classes
        self._version = version
        self._stage = stage_used
        self._loaded = True

        logger.info(
            "predictor_loaded",
            model_name=model_name,
            version=version,
            stage=stage_used,
            num_classes=num_classes,
            device=str(self._device),
        )

    # ------------------------------------------------------------------
    # Fetch class_labels.json from the run (if not embedded in state_dict)
    # ------------------------------------------------------------------
    def _load_classes_from_run(self, run_id: str) -> list[str]:
        try:
            import json

            from mlflow.artifacts import download_artifacts

            path = download_artifacts(run_id=run_id, artifact_path="class_labels.json")
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            classes = data.get("classes", [])
            if classes:
                return [str(c) for c in classes]
        except Exception:
            logger.exception("predictor_classes_fetch_failed", run_id=run_id)

        logger.warning("predictor_class_labels_unavailable")
        return []

    # ------------------------------------------------------------------
    # Predict
    # ------------------------------------------------------------------
    def predict(
        self,
        image_bytes: bytes,
        *,
        top_k: int | None = None,
    ) -> PredictionResult:
        if not self._loaded or self._model is None:
            raise MLModelError("Predictor not loaded. Call .load() first.")

        top_k = top_k or self._settings.model_top_k
        effective_num_classes = len(self._classes) if self._classes else 10
        top_k = max(1, min(top_k, effective_num_classes))

        image_hash = hashlib.sha256(image_bytes).hexdigest()
        cache_key = f"{image_hash}::{top_k}"

        cached = self._cache.get(cache_key)
        if cached is not None:
            logger.info("prediction_cache_hit", hash=image_hash[:12])
            return PredictionResult(
                category=cached.category,
                confidence=cached.confidence,
                top_k=cached.top_k,
                model_name=cached.model_name,
                model_version=cached.model_version,
                model_stage=cached.model_stage,
                cached=True,
                inference_ms=cached.inference_ms,
            )

        # Decode + preprocess
        try:
            with Image.open(io.BytesIO(image_bytes)) as img_file:
                img: Image.Image = img_file.convert("RGB")
                preprocessed = cast(Tensor, self._PREPROCESS(img))
                tensor: Tensor = preprocessed.unsqueeze(0)
        except Exception as exc:
            raise ValidationError(f"Invalid image file: {exc}") from exc

        tensor = tensor.to(self._device)

        # Inference
        t0 = time.perf_counter()
        try:
            with torch.no_grad():
                logits = self._model(tensor)
                probs = torch.softmax(logits, dim=1)[0]
                top_probs, top_indices = probs.topk(top_k)
        except Exception as exc:
            raise MLModelError(f"Inference failed: {exc}") from exc
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        top_items: list[PredictionItem] = []
        for prob, idx in zip(top_probs.tolist(), top_indices.tolist(), strict=True):
            cat = self._classes[idx] if 0 <= idx < len(self._classes) else f"class_{idx}"
            top_items.append(
                PredictionItem(
                    category=cat,
                    category_index=int(idx),
                    confidence=float(prob),
                )
            )

        result = PredictionResult(
            category=top_items[0].category,
            confidence=top_items[0].confidence,
            top_k=top_items,
            model_name=self._settings.mlflow_registered_model_name,
            model_version=self._version,
            model_stage=self._stage,
            cached=False,
            inference_ms=round(elapsed_ms, 2),
        )

        self._cache.put(cache_key, result)
        logger.info(
            "prediction_done",
            category=result.category,
            confidence=round(result.confidence, 4),
            inference_ms=result.inference_ms,
            hash=image_hash[:12],
        )
        return result

    def clear_cache(self) -> None:
        self._cache.clear()
        logger.info("predictor_cache_cleared")


# ----------------------------------------------------------------------
# Module-level singleton
# ----------------------------------------------------------------------
_predictor: CategoryPredictor | None = None
_predictor_lock = threading.Lock()


def get_predictor() -> CategoryPredictor:
    global _predictor
    with _predictor_lock:
        if _predictor is None:
            _predictor = CategoryPredictor()
        return _predictor


def load_predictor_at_startup() -> CategoryPredictor:
    """Load model at startup; log a warning on failure but don't crash."""
    predictor = get_predictor()
    try:
        predictor.load()
    except MLModelError as exc:
        logger.warning(
            "predictor_startup_load_failed",
            error=str(exc),
            hint="Predictor will retry on first /predict call.",
        )
    return predictor


def _reset_predictor_for_tests() -> None:
    global _predictor
    with _predictor_lock:
        _predictor = None
