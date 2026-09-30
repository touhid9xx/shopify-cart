"""Unit tests for ML training module — no GPU required, no training."""

from __future__ import annotations

import torch

from shopify_cart.ml.train import (
    TrainConfig,
    build_model,
    freeze_backbone,
    unfreeze_layer4,
)


def test_train_config_defaults() -> None:
    cfg = TrainConfig()
    assert cfg.batch_size == 32
    assert cfg.epochs == 5
    assert cfg.amp is True
    assert cfg.freeze_backbone_epochs == 2


def test_build_model_output_shape() -> None:
    model = build_model(num_classes=7)
    model.eval()
    x = torch.randn(2, 3, 224, 224)
    with torch.no_grad():
        y = model(x)
    assert y.shape == (2, 7)


def test_freeze_backbone_disables_grads() -> None:
    model = build_model(num_classes=3)
    freeze_backbone(model)
    for name, p in model.named_parameters():
        if name.startswith("fc."):
            assert p.requires_grad is True, f"{name} should be trainable"
        else:
            assert p.requires_grad is False, f"{name} should be frozen"


def test_unfreeze_layer4_only_layer4_and_fc() -> None:
    model = build_model(num_classes=3)
    freeze_backbone(model)
    unfreeze_layer4(model)

    for name, p in model.named_parameters():
        if name.startswith("layer4.") or name.startswith("fc."):
            assert p.requires_grad is True, f"{name} should be unfrozen"
        elif name.startswith("layer1.") or name.startswith("layer2.") or name.startswith("layer3."):
            assert p.requires_grad is False, f"{name} should stay frozen"


def test_grad_scaler_can_be_instantiated() -> None:
    """GradScaler should be constructible; disabled mode needs no GPU.

    We pick the device based on availability so this test passes both on
    local CUDA machines and on CPU-only CI runners.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    scaler = torch.amp.GradScaler(device, enabled=False)
    assert scaler is not None
    assert scaler.is_enabled() is False


def test_build_model_trainable_parameter_count() -> None:
    """Sanity: ResNet-18 has ~11.2M params; our head swap keeps it close."""
    model = build_model(num_classes=4)
    total = sum(p.numel() for p in model.parameters())
    # ResNet-18 baseline is ~11.18M; replacing fc(512->1000) with fc(512->4)
    # removes ~510K params, so expect roughly 11.17M.
    assert 11_000_000 <= total <= 11_300_000


def test_train_config_validation() -> None:
    """Custom config should override defaults cleanly."""
    cfg = TrainConfig(epochs=20, batch_size=16, lr_head=5e-4, fine_tune=True)
    assert cfg.epochs == 20
    assert cfg.batch_size == 16
    assert cfg.lr_head == 5e-4
    assert cfg.fine_tune is True
