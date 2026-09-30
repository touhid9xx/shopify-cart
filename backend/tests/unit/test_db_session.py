from __future__ import annotations

from sqlalchemy import text

from shopify_cart.db.session import SessionLocal, engine


def test_engine_is_created() -> None:
    assert engine is not None
    assert str(engine.url).startswith("mysql+pymysql://")


def test_session_factory_returns_session() -> None:
    with SessionLocal() as db:
        assert db is not None


def test_select_one_via_session() -> None:
    """If MySQL is up, SELECT 1 must work. Skipped when MySQL is not reachable."""
    try:
        with SessionLocal() as db:
            result = db.execute(text("SELECT 1")).scalar()
    except Exception as exc:  # noqa: BLE001
        import pytest

        pytest.skip(f"MySQL not available: {exc}")
    assert result == 1
