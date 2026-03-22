"""Add email column to slack_users table.

Revision ID: 002
Revises: 001
Create Date: 2026-03-20
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "slack_users",
        sa.Column("email", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("slack_users", "email")
