"""SQLAlchemy 2.0 declarative base + naming convention."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, MetaData, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, registry
from sqlalchemy.types import TypeEngine

# ----------------------------------------------------------------------
# Naming convention — ensures Alembic generates stable index/constraint
# names across environments. Without this, MySQL and PostgreSQL would
# produce different auto-generated names for the same constraint.
# ----------------------------------------------------------------------
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


TYPE_ANNOTATION_MAP: dict[type, TypeEngine[object]] = {  # noqa: var-annotated
    str: Text,  # type: ignore[dict-item]
}


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    registry = registry(type_annotation_map=TYPE_ANNOTATION_MAP)


class TimestampMixin:
    """Adds created_at / updated_at columns. All times UTC."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
