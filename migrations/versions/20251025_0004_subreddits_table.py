"""Add subreddits table

Revision ID: 20251025_0004
Revises: 20251025_0003
Create Date: 2025-10-25 01:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251025_0004"
down_revision = "20251025_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subreddits",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'active'")),
        sa.Column(
            "poll_interval_minutes",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1440"),
        ),
        sa.Column("last_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_post_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_subreddits_status", "subreddits", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subreddits_status", table_name="subreddits")
    op.drop_table("subreddits")
