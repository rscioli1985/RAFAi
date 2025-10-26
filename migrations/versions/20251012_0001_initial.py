"""Initial schema for NIL RAG MVP

Revision ID: 20251012_0001
Revises: 
Create Date: 2025-10-12 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "20251012_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector is available
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "raw_posts",
        sa.Column("id", sa.String(length=32), primary_key=True),
        sa.Column("subreddit", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_index("ix_raw_posts_subreddit", "raw_posts", ["subreddit"], unique=False)
    op.create_index("ix_raw_posts_created_utc", "raw_posts", ["created_utc"], unique=False)

    op.create_table(
        "raw_comments",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("post_id", sa.String(length=32), sa.ForeignKey("raw_posts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_index("ix_raw_comments_post_id", "raw_comments", ["post_id"], unique=False)
    op.create_index("ix_raw_comments_created_utc", "raw_comments", ["created_utc"], unique=False)

    op.create_table(
        "faqs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("source_post_id", sa.String(length=32), sa.ForeignKey("raw_posts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_utc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=64)), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_index("ix_faqs_tags", "faqs", ["tags"], unique=False)

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("counts", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("ref_id", sa.String(length=40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index("ix_documents_kind", "documents", ["kind"], unique=False)
    op.create_index("ix_documents_created_at", "documents", ["created_at"], unique=False)

    # embeddings table with pgvector column via raw SQL to avoid Python type dependency
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS embeddings (
          id BIGSERIAL PRIMARY KEY,
          document_id BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
          embedding vector(1536) NOT NULL,
          model TEXT NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    # Vector index for fast ANN search (adjust lists per .env)
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relname = 'idx_embeddings_vector'
          ) THEN
            CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
          END IF;
        END$$;
        """
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.String(length=16), nullable=False),  # 'useful' | 'not_useful'
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.execute("DROP INDEX IF EXISTS idx_embeddings_vector;")
    op.execute("DROP TABLE IF EXISTS embeddings;")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_kind", table_name="documents")
    op.drop_table("documents")
    op.drop_table("ingestion_runs")
    op.drop_index("ix_faqs_tags", table_name="faqs")
    op.drop_table("faqs")
    op.drop_index("ix_raw_comments_created_utc", table_name="raw_comments")
    op.drop_index("ix_raw_comments_post_id", table_name="raw_comments")
    op.drop_table("raw_comments")
    op.drop_index("ix_raw_posts_created_utc", table_name="raw_posts")
    op.drop_index("ix_raw_posts_subreddit", table_name="raw_posts")
    op.drop_table("raw_posts")
