"""End-to-end auth tests — needs MySQL running."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from shopify_cart.db.session import SessionLocal


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


@pytest.fixture(autouse=True)
def _require_mysql() -> None:
    """Skip the whole module if MySQL is unreachable."""
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1")).scalar()
    except SQLAlchemyError as exc:
        pytest.skip(f"MySQL not available: {exc}")


def test_register_login_me_flow(client: TestClient) -> None:
    email = _unique_email()

    # 1) Register
    r = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "full_name": "Test User"},
    )
    assert r.status_code == 201, r.text
    user = r.json()
    assert user["email"] == email
    assert user["is_admin"] is False
    assert "hashed_password" not in user
    assert "password" not in user

    # 2) Login
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret1"},
    )
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"

    # 3) /me
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    email = _unique_email()
    body = {"email": email, "password": "supersecret1"}
    r1 = client.post("/api/v1/auth/register", json=body)
    assert r1.status_code == 201
    r2 = client.post("/api/v1/auth/register", json=body)
    assert r2.status_code == 409


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert r.status_code == 401


def test_me_without_token_returns_401(client: TestClient) -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_me_with_invalid_token_returns_401(client: TestClient) -> None:
    r = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r.status_code == 401


def test_refresh_returns_new_token_pair(client: TestClient) -> None:
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret1"},
    )
    refresh_token = r.json()["refresh_token"]

    r = client.post(f"/api/v1/auth/refresh?token={refresh_token}")
    assert r.status_code == 200
    new_tokens = r.json()
    assert "access_token" in new_tokens


def test_refresh_rejects_access_token(client: TestClient) -> None:
    email = _unique_email()
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1"},
    )
    r = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret1"},
    )
    access_token = r.json()["access_token"]

    r = client.post(f"/api/v1/auth/refresh?token={access_token}")
    assert r.status_code == 401
