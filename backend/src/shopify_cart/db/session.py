"""SQLAlchemy engine + session factory (sync)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from shopify_cart.config import get_settings

_settings = get_settings()

# ----------------------------------------------------------------------
# Engine configuration
# ----------------------------------------------------------------------
# pool_pre_ping=True: before using a connection, ping it. Fixes MySQL's
# "server has gone away" error after long idle periods.
#
# pool_recycle=3600: recycle connections after 1 hour. MySQL's default
# wait_timeout is 8 hours, but connection reuse across that window can
# cause stale connections in long-running workers.
# ----------------------------------------------------------------------
engine: Engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a Session, closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
