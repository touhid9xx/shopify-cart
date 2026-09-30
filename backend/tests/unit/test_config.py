"""Tests for application settings (pydantic-settings)."""

from __future__ import annotations

import pytest

from shopify_cart.config import Settings, get_settings


def test_defaults_are_sane() -> None:
    s = Settings()
    assert s.app_name
    assert s.app_env in {"development", "staging", "production", "test"}
    assert isinstance(s.app_debug, bool)
    assert s.app_port > 0
    assert s.app_version
    assert s.jwt_algorithm == "HS256"
    assert s.jwt_access_token_expire_minutes > 0
    assert s.jwt_refresh_token_expire_days > 0
    assert 0.0 < s.model_confidence_threshold <= 1.0
    assert s.model_image_size > 0
    assert s.model_top_k > 0
    assert s.cart_max_items > 0
    assert s.cart_max_quantity_per_item > 0


def test_database_url_format() -> None:
    s = Settings(
        mysql_host="db.example.com",  # type: ignore
        mysql_port=3307,  # type: ignore
        mysql_user="alice",  # type: ignore
        mysql_password="secret",  # type: ignore
        mysql_database="shop",  # type: ignore
    )
    assert s.database_url == (
        "mysql+pymysql://alice:secret@db.example.com:3307/shop?charset=utf8mb4"
    )


def test_database_url_uses_all_fields() -> None:
    s1 = Settings(mysql_host="a")  # type: ignore
    s2 = Settings(mysql_host="b")  # type: ignore
    assert s1.database_url != s2.database_url
    assert "a" in s1.database_url
    assert "b" in s2.database_url


def test_is_production_true() -> None:
    assert Settings(app_env="production").is_production is True  # type: ignore


def test_is_production_false_for_dev() -> None:
    assert Settings(app_env="development").is_production is False  # type: ignore


def test_is_production_false_for_staging() -> None:
    assert Settings(app_env="staging").is_production is False  # type: ignore


def test_app_env_lowercased_by_validator() -> None:
    assert Settings(app_env="PRODUCTION").app_env == "production"  # type: ignore


def test_app_env_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="app_env must be one of"):
        Settings(app_env="not-a-real-env")  # type: ignore


@pytest.mark.parametrize("env", ["development", "staging", "production", "test"])
def test_app_env_accepts_allowed(env: str) -> None:
    assert Settings(app_env=env).app_env == env  # type: ignore


def test_cors_origins_default_is_list() -> None:
    s = Settings()
    assert isinstance(s.api_cors_origins, list)
    assert len(s.api_cors_origins) > 0


def test_cors_origins_from_json_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """List fields parse from JSON when they come from the env."""
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://a.com", "http://b.com"]')
    s = Settings()
    assert s.api_cors_origins == ["http://a.com", "http://b.com"]


def test_cors_origins_can_be_a_real_list_kwarg() -> None:
    s = Settings(api_cors_origins=["http://x.com"])  # type: ignore
    assert s.api_cors_origins == ["http://x.com"]


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b


def test_get_settings_cache_can_be_cleared() -> None:
    get_settings.cache_clear()
    a = get_settings()
    get_settings.cache_clear()
    b = get_settings()
    assert a is not b


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "override-name")
    assert Settings().app_name == "override-name"


def test_env_var_bool_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_ENABLED", "false")
    assert Settings().kafka_enabled is False

    monkeypatch.setenv("KAFKA_ENABLED", "true")
    assert Settings().kafka_enabled is True


def test_env_var_int_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_PORT", "9999")
    assert Settings().app_port == 9999


def test_construct_by_field_name() -> None:
    s = Settings(mysql_user="bob", kafka_client_id="my-app")  # type: ignore
    assert s.mysql_user == "bob"
    assert s.kafka_client_id == "my-app"
