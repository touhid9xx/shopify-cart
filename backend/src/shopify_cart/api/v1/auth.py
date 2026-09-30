"""Authentication endpoints: register, login, refresh, me."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select

from shopify_cart.api.deps import CurrentUser, DbSession
from shopify_cart.config import get_settings
from shopify_cart.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from shopify_cart.exceptions import AuthError, ConflictError
from shopify_cart.logging_config import get_logger
from shopify_cart.models.user import User
from shopify_cart.schemas.user import (
    TokenPair,
    UserCreate,
    UserLogin,
    UserRead,
)

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)
settings = get_settings()


def _token_expires_in() -> int:
    return settings.jwt_access_token_expire_minutes * 60


def _make_token_pair(user: User) -> TokenPair:
    sub = str(user.id)
    return TokenPair(
        access_token=create_access_token(subject=sub, email=user.email, is_admin=user.is_admin),
        refresh_token=create_refresh_token(subject=sub, email=user.email, is_admin=user.is_admin),
        expires_in=_token_expires_in(),
    )


# ----------------------------------------------------------------------
# Register
# ----------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
def register(payload: UserCreate, db: DbSession) -> User:
    existing = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_admin=False,  # promotion to admin is manual (DB / seed script)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("user_registered", user_id=user.id, email=user.email)
    return user


# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenPair,
    summary="Exchange email + password for a token pair",
)
def login(payload: UserLogin, db: DbSession) -> TokenPair:
    user = db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none()

    # NOTE: same generic message for wrong email and wrong password —
    # never leak which one is wrong.
    if user is None or not verify_password(payload.password, user.hashed_password):
        logger.warning("login_failed", email=payload.email)
        raise AuthError("Invalid email or password.")
    if not user.is_active:
        raise AuthError("User account is disabled.")

    logger.info("user_logged_in", user_id=user.id, email=user.email)
    return _make_token_pair(user)


# ----------------------------------------------------------------------
# Refresh
# ----------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Exchange a refresh token for a new token pair",
)
def refresh(
    token: str,
    db: DbSession,
) -> TokenPair:
    payload = decode_token(token, expected_type="refresh")

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Refresh token missing subject.")
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as exc:
        raise AuthError("Invalid subject in refresh token.") from exc

    user = db.get(User, user_id)
    if user is None:
        raise AuthError("User not found.")
    if not user.is_active:
        raise AuthError("User account is disabled.")

    logger.info("token_refreshed", user_id=user.id)
    return _make_token_pair(user)


# ----------------------------------------------------------------------
# Me
# ----------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the currently authenticated user",
)
def me(current_user: CurrentUser) -> User:
    return current_user
