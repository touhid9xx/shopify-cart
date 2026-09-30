"""Unit tests for ML tune module — no GPU, no real training."""

from __future__ import annotations

import uuid

import optuna
from optuna.pruners import MedianPruner
from optuna.samplers import TPESampler
from optuna.study import StudyDirection

from shopify_cart.ml.tune import TuneConfig


# ----------------------------------------------------------------------
# Config defaults
# ----------------------------------------------------------------------
def test_tune_config_defaults() -> None:
    cfg = TuneConfig()
    assert cfg.n_trials == 10
    assert cfg.epochs_per_trial == 3
    assert cfg.study_name == "shopify-category-tuning"
    assert cfg.seed == 42


# ----------------------------------------------------------------------
# Optuna study construction
# ----------------------------------------------------------------------
def test_optuna_creates_study_with_tpe_sampler() -> None:
    # Unique name per run to guarantee test isolation
    study_name = f"unit-test-study-{uuid.uuid4().hex[:8]}"
    study = optuna.create_study(
        study_name=study_name,
        direction="maximize",
        sampler=TPESampler(seed=1),
        load_if_exists=False,  # ← do not reuse
    )
    assert study.direction == StudyDirection.MAXIMIZE
    assert isinstance(study.sampler, TPESampler)


# ----------------------------------------------------------------------
# Parameter suggestions
# ----------------------------------------------------------------------
def test_optuna_trial_suggests_correct_types() -> None:
    def objective(trial: optuna.Trial) -> float:
        lr = trial.suggest_float("lr", 1e-4, 1e-2, log=True)
        bs = trial.suggest_categorical("bs", [16, 32, 64])
        opt = trial.suggest_categorical("opt", ["adamw", "sgd"])
        aug = trial.suggest_categorical("aug", [True, False])
        fe = trial.suggest_int("freeze_epochs", 0, 2)

        assert 1e-4 <= lr <= 1e-2
        assert bs in (16, 32, 64)
        assert opt in ("adamw", "sgd")
        assert isinstance(aug, bool)
        assert 0 <= fe <= 2
        return lr  # dummy value

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=3)
    assert len(study.trials) == 3
    # All trials should be complete
    assert all(t.state == optuna.trial.TrialState.COMPLETE for t in study.trials)


# ----------------------------------------------------------------------
# Pruner configuration
# ----------------------------------------------------------------------
def test_median_pruner_configuration() -> None:
    pruner = MedianPruner(n_startup_trials=2, n_warmup_steps=1)
    assert pruner is not None
    # The pruner should be attached to a study
    study = optuna.create_study(direction="maximize", pruner=pruner)
    assert isinstance(study.pruner, MedianPruner)


# ----------------------------------------------------------------------
# User attrs persistence
# ----------------------------------------------------------------------
def test_trial_user_attrs_storage() -> None:
    """Verify that user_attrs set during a trial persist on the FrozenTrial."""

    def objective(trial: optuna.Trial) -> float:
        trial.set_user_attr("mlflow_run_id", f"run-{trial.number}")
        trial.set_user_attr("custom_tag", "abc")
        return float(trial.number)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=3)

    # Every trial should have the user attrs
    for i, trial in enumerate(study.trials):
        assert trial.user_attrs["mlflow_run_id"] == f"run-{i}"
        assert trial.user_attrs["custom_tag"] == "abc"

    # Best trial should be the last (highest return value = 2)
    assert study.best_trial.number == 2
    assert study.best_trial.user_attrs["mlflow_run_id"] == "run-2"


# ----------------------------------------------------------------------
# Trial pruning
# ----------------------------------------------------------------------
def test_trial_pruning_triggers_trial_pruned() -> None:
    """A trial with poor intermediate values should be pruned by MedianPruner.

    Design: half the trials report a good (increasing) curve; the other half
    report a poor (decreasing) curve. The MedianPruner should prune the
    poor trials once it has enough information.
    """

    def objective(trial: optuna.Trial) -> float:
        # Alternate behaviour by trial number:
        # even trials → good curve, odd trials → bad curve
        is_good = trial.number % 2 == 0

        for step in range(10):
            value = 0.8 + 0.02 * step if is_good else 0.1 + 0.01 * step
            trial.report(value, step)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return 0.9 if is_good else 0.2

    study = optuna.create_study(
        direction="maximize",
        pruner=MedianPruner(n_startup_trials=2, n_warmup_steps=1),
    )
    study.optimize(objective, n_trials=6)

    # With alternating good/bad curves, at least one bad trial should be pruned.
    pruned = [t for t in study.trials if t.state == optuna.trial.TrialState.PRUNED]
    assert (
        len(pruned) >= 1
    ), f"Expected at least one pruned trial; got states: {[t.state.name for t in study.trials]}"
