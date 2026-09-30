"""Pydantic v2 schemas for users and auth."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ----------------------------------------------------------------------
# Base
# ----------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = Field(default=None, max_length=255)


# ----------------------------------------------------------------------
# Requests
# ----------------------------------------------------------------------
class UserCreate(UserBase):
    """Registration payload."""

    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    """Login payload."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


# ----------------------------------------------------------------------
# Responses
# ----------------------------------------------------------------------
class UserRead(UserBase):
    """Public user representation — never exposes password."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime


class TokenPair(BaseModel):
    """Access + refresh token pair returned by login/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenPayload(BaseModel):
    """Decoded JWT payload — used internally."""

    sub: str  # user id as string (JWT spec)
    email: str
    is_admin: bool
    type: str  # "access" or "refresh"
    exp: int
    iat: int
