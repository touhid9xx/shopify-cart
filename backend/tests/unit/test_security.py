from __future__ import annotations

import jwt
import pytest

from shopify_cart.config import get_settings
from shopify_cart.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from shopify_cart.exceptions import AuthError


def test_hash_password_produces_different_hashes() -> None:
    h1 = hash_password("secret123")
    h2 = hash_password("secret123")
    # Argon2 uses per-hash salt
    assert h1 != h2


def test_verify_password_success() -> None:
    h = hash_password("secret123")
    assert verify_password("secret123", h)


def test_verify_password_failure() -> None:
    h = hash_password("secret123")
    assert not verify_password("wrong", h)


def test_verify_password_with_garbage_hash() -> None:
    assert not verify_password("secret123", "not-a-hash")


def test_access_token_roundtrip() -> None:
    token = create_access_token(subject="42", email="a@b.com", is_admin=False)
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "42"
    assert payload["email"] == "a@b.com"
    assert payload["is_admin"] is False
    assert payload["type"] == "access"


def test_refresh_token_roundtrip() -> None:
    token = create_refresh_token(subject="42", email="a@b.com", is_admin=True)
    payload = decode_token(token, expected_type="refresh")
    assert payload["type"] == "refresh"


def test_decode_rejects_wrong_type() -> None:
    token = create_access_token(subject="42", email="a@b.com", is_admin=False)
    with pytest.raises(AuthError):
        decode_token(token, expected_type="refresh")


def test_decode_rejects_tampered_token() -> None:
    token = create_access_token(subject="42", email="a@b.com", is_admin=False)
    with pytest.raises(AuthError):
        decode_token(token + "tampered", expected_type="access")


def test_decode_rejects_expired_token() -> None:
    settings = get_settings()
    now_payload = {
        "sub": "1",
        "email": "x@y.com",
        "is_admin": False,
        "type": "access",
        "iat": 0,
        "exp": 1,  # 1970 — long expired
    }
    token = jwt.encode(
        now_payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(AuthError):
        decode_token(token, expected_type="access")
