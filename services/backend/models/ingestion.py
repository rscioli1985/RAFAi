from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class Subreddit(TimestampMixin, Base):
    __tablename__ = "subreddits"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'active'"), default="active"
    )
    poll_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1440"), default=1440
    )
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    last_post_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    keywords: Mapped[list["SubredditKeyword"]] = relationship(
        back_populates="subreddit", cascade="all, delete-orphan"
    )


class Keyword(TimestampMixin, Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    term: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'active'"), default="active"
    )

    subreddits: Mapped[list["SubredditKeyword"]] = relationship(
        back_populates="keyword", cascade="all, delete-orphan"
    )


class SubredditKeyword(TimestampMixin, Base):
    __tablename__ = "subreddit_keywords"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subreddit_id: Mapped[int] = mapped_column(
        ForeignKey("subreddits.id", ondelete="CASCADE"), nullable=False
    )
    keyword_id: Mapped[int] = mapped_column(
        ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False
    )
    relevance: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    subreddit: Mapped[Subreddit] = relationship(back_populates="keywords")
    keyword: Mapped[Keyword] = relationship(back_populates="subreddits")
