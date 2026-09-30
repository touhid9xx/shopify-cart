"""Alembic environment — reads DB URL from our Settings.

We deliberately do NOT use `config.set_main_option("sqlalchemy.url", ...)`.
Python's configparser treats `%` as string interpolation, and our
URL-encoded password contains `%40` (from quote_plus on '@'). That would
raise: ValueError: invalid interpolation syntax ...

Instead we pass the URL through `config.attributes`, which is a plain
dict with no interpolation semantics.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from shopify_cart.config import get_settings
from shopify_cart.db.base import Base
from shopify_cart.models import *  # noqa: F403, F401

# ── Alembic Config object ──────────────────────────────────
config = context.config

# Load Python logging config from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Resolve DB URL from Settings ───────────────────────────
settings = get_settings()
# NOTE: do NOT call config.set_main_option() here — see module docstring.
config.attributes["sqlalchemy_url"] = settings.database_url

# ── Metadata for autogenerate ──────────────────────────────
target_metadata = Base.metadata


# ── Offline mode ───────────────────────────────────────────
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    url = config.attributes.get("sqlalchemy_url")
    if url is None:
        raise RuntimeError("sqlalchemy_url missing from config.attributes")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ────────────────────────────────────────────
def run_migrations_online() -> None:
    """Run migrations in 'online' mode (real DB connection)."""
    url = config.attributes.get("sqlalchemy_url")
    if url is None:
        raise RuntimeError("sqlalchemy_url missing from config.attributes")

    connectable = create_engine(url, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
