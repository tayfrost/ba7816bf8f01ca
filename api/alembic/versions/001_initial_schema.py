"""initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("company_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("company_id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "subscription_plans",
        sa.Column("plan_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_name", sa.String(), nullable=False),
        sa.Column("price_pennies", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="GBP"),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint("plan_name"),
    )

    op.create_table(
        "subscriptions",
        sa.Column("subscription_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.plan_id"]),
        sa.PrimaryKeyConstraint("subscription_id"),
    )

    op.create_table(
        "users",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("company_id", "user_id"),
    )

    op.create_table(
        "auth_users",
        sa.Column("auth_user_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("auth_user_id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "slack_workspaces",
        sa.Column("slack_workspace_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.PrimaryKeyConstraint("slack_workspace_id"),
        sa.UniqueConstraint("team_id"),
    )

    op.create_table(
        "slack_accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("slack_user_id", sa.String(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["team_id"], ["slack_workspaces.team_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "slack_user_id"),
    )

    op.create_table(
        "google_mailboxes",
        sa.Column("google_mailbox_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email_address", sa.String(), nullable=False),
        sa.Column("token_json", sa.Text(), nullable=True),
        sa.Column("last_history_id", sa.String(), nullable=True),
        sa.Column("watch_expiration", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("google_mailbox_id"),
    )

    op.create_table(
        "messages",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_raw", postgresql.JSONB(), nullable=True),
        sa.Column("conversation_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("message_id"),
    )

    op.create_table(
        "incident_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("neutral_score", sa.Float(), nullable=True),
        sa.Column("humor_sarcasm_score", sa.Float(), nullable=True),
        sa.Column("stress_score", sa.Float(), nullable=True),
        sa.Column("burnout_score", sa.Float(), nullable=True),
        sa.Column("depression_score", sa.Float(), nullable=True),
        sa.Column("harassment_score", sa.Float(), nullable=True),
        sa.Column("suicidal_ideation_score", sa.Float(), nullable=True),
        sa.Column("predicted_category", sa.String(), nullable=True),
        sa.Column("predicted_severity", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["message_id"], ["messages.message_id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("incident_scores")
    op.drop_table("messages")
    op.drop_table("google_mailboxes")
    op.drop_table("slack_accounts")
    op.drop_table("slack_workspaces")
    op.drop_table("auth_users")
    op.drop_table("users")
    op.drop_table("subscriptions")
    op.drop_table("subscription_plans")
    op.drop_table("companies")
