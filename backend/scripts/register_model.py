"""
Register a run's model in the MLflow Model Registry.

All configuration comes from `.env` via Settings:
  - settings.mlflow_tracking_uri              → MLflow server URL
  - settings.mlflow_experiment_name           → Source experiment name
  - settings.mlflow_registered_model_name     → Target registry name

CLI args (optional) override the settings for one-off use:
  --tracking-uri    Override tracking server
  --experiment      Override source experiment
  --registered-name Override target registry name

Usage:
    # Explicit run_id
    python scripts/register_model.py --run-id <id> --artifact-path pytorch_model

    # Auto-pick longest training run with a model
    python scripts/register_model.py --auto

    # Add --promote to push to Production stage
    python scripts/register_model.py --auto --promote
"""

from __future__ import annotations

import argparse
import sys

import mlflow
from mlflow.tracking import MlflowClient

from shopify_cart.config import Settings, get_settings


# ----------------------------------------------------------------------
# Settings loader
# ----------------------------------------------------------------------
def load_settings() -> Settings:
    """
    Load application settings from `.env` / environment variables.

    All MLflow-related config (tracking URI, experiment name, registered
    model name) comes from here — never from hard-coded constants.
    """
    return get_settings()


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def artifact_path_for_run(
    client: MlflowClient,
    run_id: str,
    candidate_names: list[str],
) -> str | None:
    """Return the first candidate name that exists as a top-level artifact."""
    try:
        top = {a.path for a in client.list_artifacts(run_id)}
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️  list_artifacts({run_id}) failed: {exc}")
        return None

    for name in candidate_names:
        if name in top:
            return name
    return None


def auto_pick_run(
    client: MlflowClient,
    experiment_name: str,
    candidate_names: list[str],
) -> tuple[str, str]:
    """Pick the longest-duration FINISHED run that has a model artifact."""
    exp = client.get_experiment_by_name(experiment_name)
    if exp is None:
        raise RuntimeError(f"Experiment {experiment_name!r} not found.")

    runs = client.search_runs(
        experiment_ids=[exp.experiment_id],
        filter_string="attributes.status = 'FINISHED'",
        order_by=["start_time DESC"],
        max_results=100,
    )

    candidates: list[tuple[int, str, str]] = []  # (duration_ms, run_id, path)
    for r in runs:
        path = artifact_path_for_run(client, r.info.run_id, candidate_names)
        if path is None:
            continue
        dur = (r.info.end_time or 0) - (r.info.start_time or 0)
        candidates.append((dur, r.info.run_id, path))

    if not candidates:
        raise RuntimeError("No finished run with a model artifact found.")

    # Longest duration wins
    candidates.sort(reverse=True)
    _, run_id, path = candidates[0]
    return run_id, path


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    # ---- Load settings from .env ----
    settings = load_settings()

    # Candidate artifact folder names — override via CLI if needed.
    # Defaults match what train.py logs: "pytorch_model" and "model".
    default_artifact_names = ["pytorch_model", "model"]

    p = argparse.ArgumentParser(description="Register a model version.")
    p.add_argument(
        "--tracking-uri",
        default=settings.mlflow_tracking_uri,
        help=(
            "MLflow tracking URI. Defaults to MLFLOW_TRACKING_URI from .env."
        ),
    )
    p.add_argument(
        "--experiment",
        default=settings.mlflow_experiment_name,
        help=(
            "Source experiment name. Defaults to MLFLOW_EXPERIMENT_NAME "
            "from .env."
        ),
    )
    p.add_argument(
        "--registered-name",
        default=settings.mlflow_registered_model_name,
        help=(
            "Target registry name. Defaults to "
            "MLFLOW_REGISTERED_MODEL_NAME from .env."
        ),
    )
    p.add_argument("--run-id", default=None, help="Explicit run_id")
    p.add_argument(
        "--artifact-path",
        default=None,
        help="'pytorch_model' or 'model' (auto-detected if omitted)",
    )
    p.add_argument(
        "--auto",
        action="store_true",
        help="Auto-pick the longest training run with a model.",
    )
    p.add_argument(
        "--promote",
        action="store_true",
        help="Transition the new version to Production.",
    )
    args = p.parse_args(argv)

    # ---- Echo the resolved config (helps debugging) ----
    print(f"🔗 MLflow tracking URI: {args.tracking_uri}")
    print(f"🧪 Source experiment:   {args.experiment}")
    print(f"📛 Registered name:     {args.registered_name}")

    # Sync global mlflow state (used by mlflow.* module-level helpers)
    mlflow.set_tracking_uri(args.tracking_uri)

    client = MlflowClient(tracking_uri=args.tracking_uri)

    # ---- Choose run ----
    if args.auto:
        run_id, artifact_path = auto_pick_run(
            client, args.experiment, default_artifact_names
        )
        print(f"🤖 Auto-picked run: {run_id}  (artifact: {artifact_path})")
    elif args.run_id:
        run_id = args.run_id
        artifact_path = args.artifact_path or artifact_path_for_run(
            client, run_id, default_artifact_names
        )
        if artifact_path is None:
            print(f"❌ No model artifact found in run {run_id}.")
            return 1
    else:
        print("❌ Provide --run-id or --auto.")
        return 1

    model_uri = f"runs:/{run_id}/{artifact_path}"
    print(f"📦 Registering: {model_uri}")

    # ---- Ensure registered model exists ----
    try:
        client.create_registered_model(args.registered_name)
        print(f"✅ Created registered model: {args.registered_name}")
    except Exception:  # noqa: BLE001
        print(f"ℹ️  Registered model {args.registered_name!r} already exists.")

    # ---- Create version ----
    try:
        mv = client.create_model_version(
            name=args.registered_name,
            source=model_uri,
            run_id=run_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"❌ create_model_version failed: {exc}")
        return 1

    print(f"✅ Registered version {mv.version}")

    # ---- Optional promote ----
    if args.promote:
        try:
            client.transition_model_version_stage(
                name=args.registered_name,
                version=mv.version,
                stage="Production",
                archive_existing_versions=True,
            )
            final = client.get_model_version(
                args.registered_name, mv.version
            )
            print(f"🚀 Promoted v{final.version} → stage={final.current_stage}")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️  Promote failed: {exc}")
            return 1
    else:
        print("ℹ️  Not promoted. Add --promote to move to Production stage.")

    print(f"\n📍 Final: {args.registered_name} v{mv.version}")
    print(f"    source: {model_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
