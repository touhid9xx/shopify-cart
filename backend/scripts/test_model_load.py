"""Test: can we load the registered model from MLflow?"""

from __future__ import annotations

import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient


def main() -> int:
    mlflow.set_tracking_uri("http://localhost:5000")
    client = MlflowClient()

    name = "shopify-category-classifier"
    versions = client.search_model_versions(f"name='{name}'")
    print(f"Found {len(versions)} versions for {name!r}")

    for v in versions:
        print(f"  v{v.version}  run_id={v.run_id}  stage={v.current_stage}")
        try:
            model = mlflow.pytorch.load_model(
                f"models:/{name}/{v.version}"
            )
            print(f"    load OK: {type(model).__name__}")
        except Exception as e:
            msg = str(e)[:200].replace("\n", " ")
            print(f"    load FAILED: {type(e).__name__}: {msg}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
