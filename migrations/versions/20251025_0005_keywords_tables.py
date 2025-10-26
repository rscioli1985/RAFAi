"""Add keywords and subreddit_keywords tables

Revision ID: 20251025_0005
Revises: 20251025_0004
Create Date: 2025-10-25 01:25:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251025_0005"
down_revision = "20251025_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "keywords",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("term", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "subreddit_keywords",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "subreddit_id",
            sa.BigInteger(),
            sa.ForeignKey("subreddits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "keyword_id",
            sa.BigInteger(),
            sa.ForeignKey("keywords.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relevance", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("subreddit_id", "keyword_id", name="uq_subreddit_keyword"),
    )

    op.create_index("ix_keywords_status", "keywords", ["status"], unique=False)
    op.create_index("ix_subreddit_keywords_subreddit", "subreddit_keywords", ["subreddit_id"], unique=False)
    op.create_index("ix_subreddit_keywords_keyword", "subreddit_keywords", ["keyword_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subreddit_keywords_keyword", table_name="subreddit_keywords")
    op.drop_index("ix_subreddit_keywords_subreddit", table_name="subreddit_keywords")
    op.drop_table("subreddit_keywords")
    op.drop_index("ix_keywords_status", table_name="keywords")
    op.drop_table("keywords")
