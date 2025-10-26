"""Add password_hash column to users

Revision ID: 20251025_0003
Revises: 20251025_0002
Create Date: 2025-10-25 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20251025_0003"
down_revision = "20251025_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("users", "password_hash", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "password_hash")
