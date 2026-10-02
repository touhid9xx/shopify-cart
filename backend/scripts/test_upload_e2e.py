# scripts.test_upload_e2e.py


"""End-to-end test: ML-powered product upload."""


from __future__ import annotations

import glob
import json
import uuid

from sqlalchemy import text

from fastapi.testclient import TestClient

from shopify_cart.db.session import SessionLocal
from shopify_cart.main import app


def main() -> int:
    with TestClient(app) as client:
        # 1. Register a new user
        email = f"admin-{uuid.uuid4().hex[:8]}@example.com"
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "pass12345"},
        )
        if reg.status_code not in (200, 201):
            print("Register failed:", reg.status_code, reg.text)
            return 1

        # 2. Promote to admin
        with SessionLocal() as db:
            db.execute(
                text("UPDATE users SET is_admin=1 WHERE email=:e"),
                {"e": email},
            )
            db.commit()

        # 3. Login
        tokens = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "pass12345"},
        ).json()
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}

        # 4. Find a test image
        imgs = glob.glob("data/processed/test/Apparel/*.jpg")[:1]
        if not imgs:
            print("No test images found in data/processed/test/Apparel/")
            return 2

        with open(imgs[0], "rb") as f:
            img_bytes = f.read()

        # 5. POST /admin/products/upload
        response = client.post(
            "/api/v1/admin/products/upload",
            files={"image": ("shirt.jpg", img_bytes, "image/jpeg")},
            data={"name": "Test Shirt", "price": "19.99"},
            headers=headers,
        )

        print("=" * 60)
        print(f"Status: {response.status_code}")
        print("=" * 60)
        print(json.dumps(response.json(), indent=2))
        print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
