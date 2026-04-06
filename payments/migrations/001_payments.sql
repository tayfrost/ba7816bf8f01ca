-- ============================================================
-- SentinelAI Payments — Migration
--
-- PREREQUISITE: Run Derja's database migration FIRST.
-- This migration ADDS to the existing schema, not replaces it.
-- ============================================================

-- 1. Add Stripe columns to EXISTING tables (Derja's schema)
ALTER TABLE companies
    ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT UNIQUE;

ALTER TABLE subscription_plans
    ADD COLUMN IF NOT EXISTS stripe_price_id_monthly TEXT,
    ADD COLUMN IF NOT EXISTS stripe_price_id_yearly  TEXT;

-- 2. Create NEW payment-specific tables

CREATE TABLE IF NOT EXISTS stripe_subscriptions (
    id                      BIGSERIAL PRIMARY KEY,
    company_id              BIGINT NOT NULL REFERENCES companies(company_id),
    plan_id                 BIGINT NOT NULL REFERENCES subscription_plans(plan_id),
    stripe_subscription_id  TEXT UNIQUE,
    status                  TEXT NOT NULL DEFAULT 'incomplete'
                            CHECK (status IN ('active','past_due','canceled','incomplete','trialing','unpaid')),
    interval                TEXT NOT NULL DEFAULT 'month'
                            CHECK (interval IN ('month','year')),
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN DEFAULT FALSE,
    canceled_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stripe_sub_company ON stripe_subscriptions(company_id);
CREATE INDEX IF NOT EXISTS idx_stripe_sub_stripe  ON stripe_subscriptions(stripe_subscription_id);

CREATE TABLE IF NOT EXISTS payments (
    id                       BIGSERIAL PRIMARY KEY,
    company_id               BIGINT NOT NULL REFERENCES companies(company_id),
    stripe_payment_intent_id TEXT UNIQUE,
    stripe_invoice_id        TEXT UNIQUE,
    amount_pennies           BIGINT NOT NULL,
    currency                 CHAR(3) NOT NULL DEFAULT 'GBP',
    status                   TEXT NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('succeeded','pending','failed','refunded')),
    description              TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pay_company ON payments(company_id);

CREATE TABLE IF NOT EXISTS stripe_events (
    id              BIGSERIAL PRIMARY KEY,
    stripe_event_id TEXT NOT NULL UNIQUE,
    event_type      TEXT NOT NULL,
    processed       BOOLEAN DEFAULT FALSE,
    payload         TEXT,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
