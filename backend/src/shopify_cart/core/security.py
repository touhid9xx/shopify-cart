"""Password hashing and JWT utilities."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext

from shopify_cart.config import get_settings
from shopify_cart.exceptions import AuthError

settings = get_settings()


# ----------------------------------------------------------------------
# Password hashing — Argon2 (winner of Password Hashing Competition)
# ----------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2."""
    return _pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against a stored hash."""
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:  # noqa: BLE001 — see docstring; intentional catch-all
        return False


# ----------------------------------------------------------------------
# JWT
# ----------------------------------------------------------------------
TokenType = Literal["access", "refresh"]


def _create_token(
    *,
    subject: str,
    email: str,
    is_admin: bool,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "email": email,
        "is_admin": is_admin,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(*, subject: str, email: str, is_admin: bool) -> str:
    return _create_token(
        subject=subject,
        email=email,
        is_admin=is_admin,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(*, subject: str, email: str, is_admin: bool) -> str:
    return _create_token(
        subject=subject,
        email=email,
        is_admin=is_admin,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT. Raises AuthError on any problem."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Invalid token.") from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise AuthError(f"Expected {expected_type} token, got {payload.get('type')!r}.")

    return payload
