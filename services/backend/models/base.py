from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column
from sqlalchemy import DateTime, func


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    metadata: Any


class TimestampMixin:
    """Adds created/updated timestamps with DB defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class JSONBMixin:
    """Provides a metadata JSONB column for future extensibility."""

    @declared_attr
    def metadata_json(cls) -> Mapped[Dict[str, Any] | None]:  # type: ignore[override]
        from sqlalchemy.dialects.postgresql import JSONB

        return mapped_column(JSONB, nullable=True)
