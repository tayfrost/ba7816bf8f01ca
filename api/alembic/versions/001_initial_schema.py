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
    # ── subscription_plan ──────────────────────────────────────────────
    op.create_table(
        "subscription_plan",
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_name", sa.Text(), nullable=False),
        sa.Column("plan_cost_pennies", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default=sa.text("'GBP'")),
        sa.Column("max_employees", sa.BigInteger(), nullable=False),
        sa.Column("stripe_price_id_monthly", sa.Text(), nullable=True),
        sa.Column("stripe_price_id_yearly", sa.Text(), nullable=True),
        sa.CheckConstraint("char_length(trim(plan_name)) > 1", name="ck_plan_name_len"),
        sa.CheckConstraint("plan_cost_pennies >= 0", name="ck_plan_cost_nonneg"),
        sa.CheckConstraint("max_employees > 0", name="ck_max_employees_pos"),
        sa.PrimaryKeyConstraint("plan_id"),
        sa.UniqueConstraint("plan_name"),
    )

    # ── companies ──────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("company_name", sa.Text(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.CheckConstraint("char_length(trim(company_name)) > 1", name="ck_company_name_len"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plan.plan_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("company_id"),
        sa.UniqueConstraint("stripe_customer_id"),
    )

    # ── saas_user_data ─────────────────────────────────────────────────
    op.create_table(
        "saas_user_data",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("surname", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.CheckConstraint("char_length(trim(name)) > 1", name="ck_saas_name_len"),
        sa.CheckConstraint("char_length(trim(surname)) > 1", name="ck_saas_surname_len"),
        sa.CheckConstraint(
            "char_length(trim(email)) > 3 AND position('@' in trim(email)) > 1 "
            "AND position('@' in trim(email)) < char_length(trim(email))",
            name="ck_saas_email",
        ),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
    )

    # ── saas_company_roles ─────────────────────────────────────────────
    op.create_table(
        "saas_company_roles",
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.CheckConstraint("role IN ('admin','viewer','biller')", name="ck_company_role"),
        sa.CheckConstraint("status IN ('active','inactive','removed')", name="ck_company_role_status"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["saas_user_data.user_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("company_id", "user_id", "role"),
    )

    # ── subscriptions ──────────────────────────────────────────────────
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'incomplete'")),
        sa.Column("interval", sa.Text(), nullable=False, server_default=sa.text("'month'")),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), default=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('active','past_due','canceled','incomplete','trialing','unpaid')",
            name="ck_subscription_status",
        ),
        sa.CheckConstraint("interval IN ('month','year')", name="ck_subscription_interval"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plan.plan_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )

    # ── slack_workspaces ───────────────────────────────────────────────
    op.create_table(
        "slack_workspaces",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Text(), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id"),
    )

    # ── slack_users ────────────────────────────────────────────────────
    op.create_table(
        "slack_users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Text(), nullable=False),
        sa.Column("slack_user_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("surname", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.CheckConstraint("char_length(trim(name)) > 1", name="ck_slack_user_name_len"),
        sa.CheckConstraint("char_length(trim(surname)) > 1", name="ck_slack_user_surname_len"),
        sa.CheckConstraint("status IN ('active','inactive','removed')", name="ck_slack_user_status"),
        sa.ForeignKeyConstraint(["team_id"], ["slack_workspaces.team_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("team_id", "slack_user_id", name="uq_slack_users_team_user"),
    )

    # ── flagged_incidents ──────────────────────────────────────────────
    op.create_table(
        "flagged_incidents",
        sa.Column("incident_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("team_id", sa.Text(), nullable=False),
        sa.Column("slack_user_id", sa.Text(), nullable=False),
        sa.Column("message_ts", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("channel_id", sa.Text(), nullable=False),
        sa.Column("raw_message_text", postgresql.JSONB(), nullable=False),
        sa.Column("class_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["team_id"], ["slack_workspaces.team_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["team_id", "slack_user_id"],
            ["slack_users.team_id", "slack_users.slack_user_id"],
            name="fk_flagged_incidents_tracker",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("incident_id"),
    )
    op.create_index(
        "idx_flagged_incidents_company_created_at",
        "flagged_incidents",
        ["company_id", "created_at"],
    )
    op.create_index(
        "idx_flagged_incidents_team_user_created_at",
        "flagged_incidents",
        ["team_id", "slack_user_id", "created_at"],
    )

    # ── google_mailboxes ───────────────────────────────────────────────
    op.create_table(
        "google_mailboxes",
        sa.Column("google_mailbox_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("email_address", sa.Text(), nullable=False),
        sa.Column("token_json", sa.Text(), nullable=True),
        sa.Column("last_history_id", sa.Text(), nullable=True),
        sa.Column("watch_expiration", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["saas_user_data.user_id"]),
        sa.PrimaryKeyConstraint("google_mailbox_id"),
    )

    # ── payments ───────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("stripe_payment_intent_id", sa.Text(), nullable=True),
        sa.Column("stripe_invoice_id", sa.Text(), nullable=True),
        sa.Column("amount_pennies", sa.BigInteger(), nullable=False),
        sa.Column("currency", sa.CHAR(3), nullable=False, server_default=sa.text("'GBP'")),
        sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "status IN ('succeeded','pending','failed','refunded')",
            name="ck_payment_status",
        ),
        sa.ForeignKeyConstraint(["company_id"], ["companies.company_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_payment_intent_id"),
        sa.UniqueConstraint("stripe_invoice_id"),
    )

    # ── stripe_events ──────────────────────────────────────────────────
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("stripe_event_id", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("processed", sa.Boolean(), default=False),
        sa.Column("payload", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_events")
    op.drop_table("payments")
    op.drop_table("google_mailboxes")
    op.drop_index("idx_flagged_incidents_team_user_created_at", table_name="flagged_incidents")
    op.drop_index("idx_flagged_incidents_company_created_at", table_name="flagged_incidents")
    op.drop_table("flagged_incidents")
    op.drop_table("slack_users")
    op.drop_table("slack_workspaces")
    op.drop_table("subscriptions")
    op.drop_table("saas_company_roles")
    op.drop_table("saas_user_data")
    op.drop_table("companies")
    op.drop_table("subscription_plan")
