"""FastAPI dependencies for authentication and authorization."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from shopify_cart.core.security import decode_token
from shopify_cart.db.session import get_db
from shopify_cart.exceptions import AuthError, PermissionDeniedError
from shopify_cart.models.user import User

DbSession = Annotated[Session, Depends(get_db)]


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise AuthError("Missing Authorization header.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthError("Authorization header must be 'Bearer <token>'.")
    return parts[1]


def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    """Resolve the authenticated user from the Bearer access token."""
    token = _extract_bearer(authorization)
    payload = decode_token(token, expected_type="access")

    user_id_raw = payload.get("sub")
    if not user_id_raw:
        raise AuthError("Token missing subject.")
    try:
        user_id = int(user_id_raw)
    except (TypeError, ValueError) as exc:
        raise AuthError("Invalid subject in token.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AuthError("User not found.")
    if not user.is_active:
        raise AuthError("User account is disabled.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin(user: CurrentUser) -> User:
    """Require admin role — otherwise 403."""
    if not user.is_admin:
        raise PermissionDeniedError("Admin privileges required.")
    return user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
