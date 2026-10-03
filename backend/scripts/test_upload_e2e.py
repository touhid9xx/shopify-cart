# scripts/test_upload_e2e.py
"""End-to-end test: ML-powered product upload.

Run from backend/:
    python scripts/test_upload_e2e.py

Requirements:
    - MySQL running (the app DB)
    - MLflow server running at MLFLOW_TRACKING_URI with a registered model
    - ML_ENABLED=true in .env
    - At least one image under data/processed/** or data/uploads/
"""

from __future__ import annotations

import json
import mimetypes
import sys
import uuid
from pathlib import Path

from sqlalchemy import text

from fastapi.testclient import TestClient

from shopify_cart.config import get_settings
from shopify_cart.db.session import SessionLocal
from shopify_cart.main import app


# ─── Helpers ─────────────────────────────────────────────────────────
def find_test_image() -> Path | None:
    """Locate any usable image for the upload test."""
    candidates = [
        "data/processed/test",
        "data/processed/val",
        "data/uploads",
    ]
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
    for base in candidates:
        base_path = Path(base)
        if not base_path.is_dir():
            continue
        for ext in extensions:
            matches = sorted(base_path.rglob(ext))
            if matches:
                return matches[0]
    return None


def fail(msg: str, code: int = 1) -> int:
    print(f"\n✗ FAIL: {msg}", file=sys.stderr)
    return code


# ─── Main ────────────────────────────────────────────────────────────
def main() -> int:
    settings = get_settings()

    # ── Pre-flight checks ──
    print("─" * 60)
    print("Pre-flight")
    print("─" * 60)
    print(f"  ml_enabled:     {settings.ml_enabled}")
    print(f"  tracking_uri:   {settings.mlflow_tracking_uri}")
    print(f"  registered:     {settings.mlflow_registered_model_name}")

    if not settings.ml_enabled:
        print(
            "\n⚠  ML_ENABLED is false. The upload endpoint may not run "
            "auto-categorization. Set ML_ENABLED=true in .env to test "
            "the full ML path.",
        )

    img_path = find_test_image()
    if img_path is None:
        return fail(
            "No test image found. Looked under "
            "data/processed/{test,val} and data/uploads."
        )
    img_bytes = img_path.read_bytes()
    mime, _ = mimetypes.guess_type(str(img_path))
    mime = mime or "application/octet-stream"
    print(f"  test image:     {img_path} ({mime}, {len(img_bytes)} bytes)")

    test_email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
    created_user = False

    try:
        with TestClient(app) as client:
            # ── 1. Register ──
            print("\n" + "─" * 60)
            print("1. Register user")
            print("─" * 60)
            reg = client.post(
                "/api/v1/auth/register",
                json={"email": test_email, "password": "pass12345"},
            )
            if reg.status_code not in (200, 201):
                return fail(
                    f"register returned {reg.status_code}: {reg.text}"
                )
            created_user = True
            print(f"  ✓ registered {test_email}")

            # ── 2. Promote to admin ──
            print("\n" + "─" * 60)
            print("2. Promote to admin")
            print("─" * 60)
            with SessionLocal() as db:
                res = db.execute(
                    text("UPDATE users SET is_admin=1 WHERE email=:e"),
                    {"e": test_email},
                )
                db.commit()
                if res.rowcount == 0:
                    return fail("promote UPDATE affected 0 rows.")
            print("  ✓ is_admin=1")

            # ── 3. Login ──
            print("\n" + "─" * 60)
            print("3. Login")
            print("─" * 60)
            login = client.post(
                "/api/v1/auth/login",
                json={"email": test_email, "password": "pass12345"},
            )
            if login.status_code != 200:
                return fail(
                    f"login returned {login.status_code}: {login.text}"
                )
            tokens = login.json()
            access = tokens.get("access_token")
            if not access:
                return fail(
                    f"login response missing access_token: {tokens}"
                )
            headers = {"Authorization": f"Bearer {access}"}
            print("  ✓ token acquired")

            # ── 4. POST /admin/products/upload ──
            print("\n" + "─" * 60)
            print("4. POST /admin/products/upload")
            print("─" * 60)
            response = client.post(
                "/api/v1/admin/products/upload",
                files={"image": (img_path.name, img_bytes, mime)},
                data={"name": "Test Shirt (e2e)", "price": "19.99"},
                headers=headers,
            )

            print(f"  status: {response.status_code}")
            try:
                body = response.json()
            except Exception:
                body = {"raw": response.text}

            print(json.dumps(body, indent=2, default=str))

            # ── Assertions ──
            if response.status_code not in (200, 201):
                return fail(
                    f"upload returned {response.status_code}: "
                    f"{json.dumps(body)[:500]}"
                )

            if "status" not in body:
                return fail(
                    f"upload response missing 'status' key: {body}"
                )

            expected_statuses = {"created", "needs_review"}
            if body["status"] not in expected_statuses:
                return fail(
                    f"unexpected status value {body['status']!r}; "
                    f"expected one of {expected_statuses}"
                )

            if body["status"] == "created":
                # Expect a product payload back
                if "product" not in body and "id" not in body:
                    return fail(
                        "status=created but no product/id in response."
                    )
                pid = body.get("product", {}).get("id") or body.get("id")
                print(f"\n  ✓ product created (id={pid})")
            else:
                # needs_review — ML uncertainty
                print(
                    "\n  ⚠  ML returned needs_review — this is valid but "
                    "check the confidence score and the returned "
                    "suggested category.",
                )

        print("\n✓ PASS: upload e2e completed.")
        return 0

    finally:
        # ── Cleanup: delete the test user ──
        if created_user:
            try:
                with SessionLocal() as db:
                    db.execute(
                        text("DELETE FROM users WHERE email=:e"),
                        {"e": test_email},
                    )
                    db.commit()
                print(f"\n🧹 Cleaned up user {test_email}")
            except Exception as exc:  # noqa: BLE001
                print(f"\n⚠  Cleanup failed for {test_email}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
