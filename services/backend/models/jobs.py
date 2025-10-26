from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from services.common.config import settings

from .base import Base, TimestampMixin, JSONBMixin


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    dag_id: Mapped[str] = mapped_column(String(255), nullable=False)
    airflow_run_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    conf: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    error: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    cost_estimate_cents: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[List["JobEvent"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobEvent.occurred_at",
    )
    posts: Mapped[List["Post"]] = relationship(back_populates="job")
    comments: Mapped[List["Comment"]] = relationship(back_populates="job")
    analyses: Mapped[List["Analysis"]] = relationship(back_populates="job")
    embeddings: Mapped[List["Embedding"]] = relationship(back_populates="job")


class JobEvent(Base):
    __tablename__ = "job_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    airflow_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=text("now()"),
        nullable=False,
    )

    job: Mapped[Job] = relationship(back_populates="events")


class Post(JSONBMixin, TimestampMixin, Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    subreddit: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    job: Mapped[Optional[Job]] = relationship(back_populates="posts")
    comments: Mapped[List["Comment"]] = relationship(back_populates="post", cascade="all, delete-orphan")
    analyses: Mapped[List["Analysis"]] = relationship(back_populates="post", cascade="all, delete-orphan")


class Comment(JSONBMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    author: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    job: Mapped[Optional[Job]] = relationship(back_populates="comments")
    post: Mapped["Post"] = relationship(back_populates="comments")
    analyses: Mapped[List["Analysis"]] = relationship(back_populates="comment", cascade="all, delete-orphan")


class Analysis(JSONBMixin, TimestampMixin, Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    post_id: Mapped[Optional[int]] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    comment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text(), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    job: Mapped[Optional[Job]] = relationship(back_populates="analyses")
    post: Mapped[Optional[Post]] = relationship(back_populates="analyses")
    comment: Mapped[Optional["Comment"]] = relationship(back_populates="analyses")
    embeddings: Mapped[List["Embedding"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
    )


class Embedding(TimestampMixin, Base):
    __tablename__ = "job_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    analysis_id: Mapped[int] = mapped_column(
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(settings.vector_dim), nullable=False)
    dims: Mapped[int] = mapped_column(Integer, nullable=False, default=settings.vector_dim)
    score: Mapped[Optional[Numeric]] = mapped_column(Numeric(10, 5), nullable=True)

    job: Mapped[Optional[Job]] = relationship(back_populates="embeddings")
    analysis: Mapped["Analysis"] = relationship(back_populates="embeddings")
