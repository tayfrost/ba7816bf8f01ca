-- ============================================================
-- SentinelAI Payments — Database Migration
-- Run against: sentinelai database (PostgreSQL 16)
--
-- NOTE: SQLAlchemy auto-creates these tables on app startup.
--       This file exists for documentation and manual use.
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ──────────────────────────────────────────────
-- Organizations (companies that subscribe)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255) UNIQUE,
    is_active       BOOLEAN DEFAULT TRUE,
    employee_count  INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_org_stripe_customer ON organizations(stripe_customer_id);

-- ──────────────────────────────────────────────
-- Subscription Plans (pricing tiers)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscription_plans (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                    VARCHAR(100) NOT NULL UNIQUE,
    description             TEXT,
    price_monthly           NUMERIC(10,2) NOT NULL,
    price_yearly            NUMERIC(10,2) NOT NULL,
    max_employees           INTEGER NOT NULL,
    stripe_price_id_monthly VARCHAR(255),
    stripe_price_id_yearly  VARCHAR(255),
    features                TEXT,           -- JSON array of feature strings
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

-- ──────────────────────────────────────────────
-- Subscriptions (active org ↔ plan links)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS subscriptions (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id         UUID NOT NULL REFERENCES organizations(id),
    plan_id                 UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id  VARCHAR(255) UNIQUE,
    status                  VARCHAR(20) DEFAULT 'incomplete'
                            CHECK (status IN ('active','past_due','canceled','incomplete','trialing','unpaid')),
    interval                VARCHAR(5) DEFAULT 'month'
                            CHECK (interval IN ('month','year')),
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN DEFAULT FALSE,
    canceled_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sub_org ON subscriptions(organization_id);
CREATE INDEX IF NOT EXISTS idx_sub_stripe ON subscriptions(stripe_subscription_id);

-- ──────────────────────────────────────────────
-- Payments (transaction history)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS payments (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id             UUID NOT NULL REFERENCES organizations(id),
    stripe_payment_intent_id    VARCHAR(255) UNIQUE,
    stripe_invoice_id           VARCHAR(255) UNIQUE,
    amount                      NUMERIC(10,2) NOT NULL,
    currency                    VARCHAR(3) DEFAULT 'gbp',
    status                      VARCHAR(20) DEFAULT 'pending'
                                CHECK (status IN ('succeeded','pending','failed','refunded')),
    description                 TEXT,
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pay_org ON payments(organization_id);
CREATE INDEX IF NOT EXISTS idx_pay_stripe_pi ON payments(stripe_payment_intent_id);

-- ──────────────────────────────────────────────
-- Stripe Events (webhook idempotency log)
-- ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stripe_events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stripe_event_id VARCHAR(255) NOT NULL UNIQUE,
    event_type      VARCHAR(255) NOT NULL,
    processed       BOOLEAN DEFAULT FALSE,
    payload         TEXT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_se_stripe_id ON stripe_events(stripe_event_id);
