"""Add orchestration job + content tables

Revision ID: 20251025_0006
Revises: 20251025_0005
Create Date: 2025-10-25 02:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = "20251025_0006"
down_revision = "20251025_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "owner_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("dag_id", sa.String(length=255), nullable=False),
        sa.Column("airflow_run_id", sa.String(length=255), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("conf", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("cost_estimate_cents", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"], unique=False)
    op.create_index("ix_jobs_owner", "jobs", ["owner_user_id"], unique=False)
    op.create_index("ix_jobs_org", "jobs", ["organization_id"], unique=False)

    op.create_table(
        "job_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("airflow_task_id", sa.String(length=255), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_job_events_job", "job_events", ["job_id"], unique=False)

    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=64), nullable=False, unique=True),
        sa.Column("subreddit", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_posts_job_id", "posts", ["job_id"], unique=False)
    op.create_index("ix_posts_org_id", "posts", ["organization_id"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_id", sa.String(length=80), nullable=False, unique=True),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_comments_job_id", "comments", ["job_id"], unique=False)
    op.create_index("ix_comments_post_id", "comments", ["post_id"], unique=False)

    op.create_table(
        "analyses",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("post_id", sa.BigInteger(), sa.ForeignKey("posts.id", ondelete="CASCADE"), nullable=True),
        sa.Column("comment_id", sa.BigInteger(), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("sentiment", sa.String(length=32), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_analyses_job_id", "analyses", ["job_id"], unique=False)
    op.create_index("ix_analyses_post_id", "analyses", ["post_id"], unique=False)
    op.create_index("ix_analyses_comment_id", "analyses", ["comment_id"], unique=False)

    op.create_table(
        "job_embeddings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("analysis_id", sa.BigInteger(), sa.ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("vector", Vector(1536), nullable=False),
        sa.Column("dims", sa.Integer(), nullable=False, server_default=sa.text("1536")),
        sa.Column("score", sa.Numeric(10, 5), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_job_embeddings_vector",
        "job_embeddings",
        ["vector"],
        unique=False,
        postgresql_using="ivfflat",
        postgresql_with={"lists": "100"},
        postgresql_ops={"vector": "vector_l2_ops"},
    )
    op.create_index("ix_job_embeddings_job_id", "job_embeddings", ["job_id"], unique=False)
    op.create_index("ix_job_embeddings_analysis_id", "job_embeddings", ["analysis_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_job_embeddings_analysis_id", table_name="job_embeddings")
    op.drop_index("ix_job_embeddings_job_id", table_name="job_embeddings")
    op.drop_index("ix_job_embeddings_vector", table_name="job_embeddings")
    op.drop_table("job_embeddings")

    op.drop_index("ix_analyses_comment_id", table_name="analyses")
    op.drop_index("ix_analyses_post_id", table_name="analyses")
    op.drop_index("ix_analyses_job_id", table_name="analyses")
    op.drop_table("analyses")

    op.drop_index("ix_comments_post_id", table_name="comments")
    op.drop_index("ix_comments_job_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_posts_org_id", table_name="posts")
    op.drop_index("ix_posts_job_id", table_name="posts")
    op.drop_table("posts")

    op.drop_index("ix_job_events_job", table_name="job_events")
    op.drop_table("job_events")

    op.drop_index("ix_jobs_org", table_name="jobs")
    op.drop_index("ix_jobs_owner", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_table("jobs")
