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
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

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


def _extract_product_id(body: dict[str, Any]) -> int | None:
    """Pull product id from either response shape.

    - Flat:   {"status": "created", "product_id": 101, ...}
    - Nested: {"status": "created", "product": {"id": 101, ...}}
    """
    product_id = body.get("product_id")
    if isinstance(product_id, int):
        return product_id

    product = body.get("product")
    if isinstance(product, dict):
        nested_id = product.get("id")
        if isinstance(nested_id, int):
            return nested_id

    flat_id = body.get("id")
    if isinstance(flat_id, int):
        return flat_id

    return None


def _parse_json_dict(response_text: str, fallback_key: str = "raw") -> dict[str, Any]:
    """Parse JSON from a response into a dict, or fall back to a wrapper."""
    try:
        parsed: Any = json.loads(response_text)
    except Exception:
        return {fallback_key: response_text}
    if isinstance(parsed, dict):
        return parsed
    return {fallback_key: parsed}


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
    created_product_id: int | None = None

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
                db.execute(
                    text("UPDATE users SET is_admin=1 WHERE email=:e"),
                    {"e": test_email},
                )
                db.commit()

            # Re-read to confirm
            with SessionLocal() as db:
                row = db.execute(
                    text("SELECT is_admin FROM users WHERE email=:e"),
                    {"e": test_email},
                ).first()
                if row is None:
                    return fail(
                        f"user {test_email} not found after promote."
                    )
                if not row.is_admin:
                    return fail(
                        f"user {test_email} is still not admin."
                    )

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
            tokens: dict[str, Any] = login.json()
            access = tokens.get("access_token")
            if not isinstance(access, str) or not access:
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
            body: dict[str, Any] = _parse_json_dict(response.text)

            print(json.dumps(body, indent=2, default=str))

            # ── Assertions: HTTP status ──
            if response.status_code not in (200, 201):
                return fail(
                    f"upload returned {response.status_code}: "
                    f"{json.dumps(body, default=str)[:500]}"
                )

            # ── Assertions: response shape ──
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

            # ── Branch on created vs needs_review ──
            if body["status"] == "created":
                pid = _extract_product_id(body)
                if pid is None:
                    return fail(
                        "status=created but response has no product id. "
                        "Expected one of: product_id, product.id, id. "
                        f"Keys present: {sorted(body.keys())}"
                    )
                created_product_id = pid
                print(f"\n  ✓ product created (id={pid})")

                # Verify the product row exists in DB
                with SessionLocal() as db:
                    row = db.execute(
                        text(
                            "SELECT id, sku, review_status, "
                            "ml_category_slug, ml_confidence, category_id "
                            "FROM products WHERE id=:id"
                        ),
                        {"id": pid},
                    ).first()
                if row is None:
                    return fail(
                        f"product {pid} not found in DB after upload."
                    )
                print(
                    f"  ✓ DB row: sku={row.sku} "
                    f"status={row.review_status} "
                    f"ml_slug={row.ml_category_slug} "
                    f"ml_conf={row.ml_confidence} "
                    f"cat_id={row.category_id}"
                )
            else:
                # needs_review — ML uncertainty or no matching category
                print(
                    "\n  ⚠  ML returned needs_review — valid but requires "
                    "admin attention.",
                )
                confidence = body.get("confidence")
                threshold = body.get("threshold")
                if isinstance(confidence, (int, float)) and isinstance(
                    threshold, (int, float)
                ):
                    print(
                        f"     confidence={confidence:.4f} "
                        f"threshold={threshold:.2f}",
                    )

                suggestions = body.get("suggestions")
                if isinstance(suggestions, list):
                    print("     suggestions:")
                    for s in suggestions:
                        if not isinstance(s, dict):
                            continue
                        cat = s.get("category", "?")
                        conf = s.get("confidence", 0.0)
                        print(f"       {cat}: {conf:.4f}")

        print("\n✓ PASS: upload e2e completed.")
        return 0

    finally:
        # ── Cleanup: delete created product, then the test user ──
        if created_product_id is not None:
            try:
                with SessionLocal() as db:
                    # Delete inventories first (FK), then the product
                    db.execute(
                        text("DELETE FROM inventories WHERE product_id=:p"),
                        {"p": created_product_id},
                    )
                    db.execute(
                        text("DELETE FROM products WHERE id=:p"),
                        {"p": created_product_id},
                    )
                    db.commit()
                print(f"\n🧹 Cleaned up product {created_product_id}")
            except Exception as exc:  # noqa: BLE001
                print(
                    f"\n⚠  Product cleanup failed for "
                    f"{created_product_id}: {exc}",
                )

        if created_user:
            try:
                with SessionLocal() as db:
                    db.execute(
                        text("DELETE FROM users WHERE email=:e"),
                        {"e": test_email},
                    )
                    db.commit()
                print(f"🧹 Cleaned up user {test_email}")
            except Exception as exc:  # noqa: BLE001
                print(f"⚠  User cleanup failed for {test_email}: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
