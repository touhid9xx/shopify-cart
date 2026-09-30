"""Tests for the exception hierarchy and FastAPI exception handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shopify_cart.exceptions import (
    AppError,
    AuthError,
    CartError,
    InventoryError,
    MLModelError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    register_exception_handlers,
)


# ----------------------------------------------------------------------
# Fixture: minimal FastAPI app with raising routes
# ----------------------------------------------------------------------
@pytest.fixture
def error_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise/not-found")
    async def _nf() -> None:
        raise NotFoundError("Product 42 not found")

    @app.get("/raise/auth")
    async def _auth() -> None:
        raise AuthError()

    @app.get("/raise/cart")
    async def _cart() -> None:
        raise CartError("Cart is empty")

    @app.get("/raise/inventory")
    async def _inv() -> None:
        raise InventoryError("Not enough stock")

    @app.get("/raise/permission")
    async def _perm() -> None:
        raise PermissionDeniedError()

    @app.get("/raise/validation")
    async def _val() -> None:
        raise ValidationError("Bad input")

    @app.get("/raise/ml")
    async def _ml() -> None:
        raise MLModelError("Model not loaded")

    @app.get("/raise/generic")
    async def _generic() -> None:
        raise RuntimeError("boom")

    return app


# ----------------------------------------------------------------------
# HTTP response shape tests
# ----------------------------------------------------------------------
def test_not_found_shape(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/not-found")

    assert r.status_code == NotFoundError.status_code
    body = r.json()
    assert set(body.keys()) == {"error", "status", "detail", "path"}
    assert body["error"] == NotFoundError.error_code
    assert body["status"] == NotFoundError.status_code
    assert body["detail"] == "Product 42 not found"
    assert body["path"] == "/raise/not-found"


def test_auth_error_default_message(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/auth")

    assert r.status_code == AuthError.status_code
    assert r.status_code == 401
    body = r.json()
    assert body["error"] == AuthError.error_code
    assert body["detail"] == AuthError.message


def test_cart_error(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/cart")

    assert r.status_code == CartError.status_code
    assert r.json()["detail"] == "Cart is empty"


def test_inventory_error(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/inventory")

    assert r.status_code == InventoryError.status_code
    assert r.status_code == 409
    assert r.json()["error"] == InventoryError.error_code


def test_permission_denied(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/permission")

    assert r.status_code == PermissionDeniedError.status_code
    assert r.status_code == 403
    assert r.json()["detail"] == PermissionDeniedError.message


def test_validation_error_shape(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/validation")

    assert r.status_code == ValidationError.status_code
    assert r.json()["error"] == ValidationError.error_code


def test_ml_model_error_shape(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/ml")

    assert r.status_code == MLModelError.status_code
    assert r.status_code == 503
    body = r.json()
    assert body["error"] == MLModelError.error_code
    assert body["detail"] == "Model not loaded"
    assert body["path"] == "/raise/ml"


def test_generic_exception_is_wrapped(error_app: FastAPI) -> None:
    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/generic")

    assert r.status_code == 500
    body = r.json()
    assert body["error"] == "internal_error"
    assert "boom" not in body["detail"]
    assert body["path"] == "/raise/generic"


# ----------------------------------------------------------------------
# Class hierarchy tests
# ----------------------------------------------------------------------
def test_app_error_hierarchy() -> None:
    for cls in (
        NotFoundError,
        ValidationError,
        AuthError,
        PermissionDeniedError,
        CartError,
        InventoryError,
        MLModelError,
    ):
        assert issubclass(cls, AppError)


# ----------------------------------------------------------------------
# Default / custom message tests
# ----------------------------------------------------------------------
def test_app_error_default_message_is_used_when_missing() -> None:
    """No-arg construction should keep the class-level default message."""
    err = AuthError()
    assert err.message == AuthError.message
    # super().__init__ sets Exception.args[0] to the resolved message
    assert str(err) == AuthError.message


def test_app_error_custom_message_overrides_default() -> None:
    err = AuthError("Token expired")
    assert err.message == "Token expired"
    assert str(err) == "Token expired"


# ----------------------------------------------------------------------
# `detail` payload tests (structured context)
# ----------------------------------------------------------------------
def test_app_error_detail_defaults_to_none() -> None:
    assert CartError("empty").detail is None


def test_app_error_detail_is_stored() -> None:
    err = InventoryError("low stock", detail={"available": 3})
    assert err.detail == {"available": 3}


def test_app_error_detail_renders_in_response(error_app: FastAPI) -> None:
    """The optional `detail` payload appears in the JSON as `extra`."""

    @error_app.get("/raise/detail")
    async def _d() -> None:
        raise InventoryError("low stock", detail={"available": 3})

    with TestClient(error_app, raise_server_exceptions=False) as c:
        r = c.get("/raise/detail")

    body = r.json()
    assert body["error"] == "inventory_error"
    assert body["detail"] == "low stock"
    assert body["extra"] == {"available": 3}
