import os
import psycopg

DB_URL = f"postgresql://postgres:{os.environ['POSTGRES_PASSWORD']}@pgvector:5432/sentinelai"

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS companies (
  company_id         BIGSERIAL PRIMARY KEY,
  name               TEXT NOT NULL UNIQUE,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at         TIMESTAMPTZ NULL,
  stripe_customer_id TEXT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS subscription_plans (
  plan_id                 BIGSERIAL PRIMARY KEY,
  plan_name               TEXT NOT NULL UNIQUE,
  price_pennies           BIGINT NOT NULL CHECK (price_pennies >= 0),
  currency                CHAR(3) NOT NULL DEFAULT 'GBP',
  seat_limit              INT NOT NULL CHECK (seat_limit > 0),
  stripe_price_id_monthly TEXT NULL,
  stripe_price_id_yearly  TEXT NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
  subscription_id      BIGSERIAL PRIMARY KEY,
  company_id           BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  plan_id              BIGINT NOT NULL REFERENCES subscription_plans(plan_id) ON DELETE RESTRICT,
  status               TEXT NOT NULL CHECK (status IN ('trialing','active','past_due','canceled')),
  current_period_start TIMESTAMPTZ NOT NULL,
  current_period_end   TIMESTAMPTZ NOT NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_subscriptions_one_per_company
  ON subscriptions(company_id);

-- above means only one subscription per comany 

-- users section:   
CREATE TABLE IF NOT EXISTS users (
  user_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id   BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  display_name TEXT NULL,
  deleted_at   TIMESTAMPTZ NULL,
  role         TEXT NOT NULL CHECK (role IN ('admin','biller','viewer')),
  status       TEXT NOT NULL CHECK (status IN ('active','inactive'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_company_user
  ON users(company_id, user_id);

CREATE INDEX IF NOT EXISTS idx_users_company
  ON users(company_id);


CREATE TABLE IF NOT EXISTS slack_workspaces (
  slack_workspace_id BIGSERIAL PRIMARY KEY,
  company_id         BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  team_id            TEXT NOT NULL UNIQUE,
  access_token       TEXT NOT NULL,
  installed_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  revoked_at         TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_slack_workspaces_company
  ON slack_workspaces(company_id);

-- Enables composite FK (company_id, team_id)
CREATE UNIQUE INDEX IF NOT EXISTS uq_slack_workspaces_company_team
  ON slack_workspaces(company_id, team_id);

CREATE TABLE IF NOT EXISTS slack_accounts (
  company_id   BIGINT NOT NULL,
  team_id      TEXT NOT NULL,
  slack_user_id TEXT NOT NULL,
  user_id      UUID NOT NULL,
  email        CITEXT NULL,
  PRIMARY KEY (team_id, slack_user_id),

  -- team belongs to the same company
  CONSTRAINT fk_slack_accounts_company_team
    FOREIGN KEY (company_id, team_id)
    REFERENCES slack_workspaces(company_id, team_id)
    ON DELETE RESTRICT,

  -- user belongs to the same company
  CONSTRAINT fk_slack_accounts_company_user
    FOREIGN KEY (company_id, user_id)
    REFERENCES users(company_id, user_id)
    ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_slack_accounts_user
  ON slack_accounts(user_id);

CREATE INDEX IF NOT EXISTS idx_slack_accounts_company
  ON slack_accounts(company_id);

CREATE TABLE IF NOT EXISTS google_mailboxes (
  google_mailbox_id BIGSERIAL PRIMARY KEY,
  company_id        BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  user_id           UUID NOT NULL,
  email_address     CITEXT NOT NULL,
  token_json        JSONB NOT NULL,
  last_history_id   TEXT NULL,
  watch_expiration  TIMESTAMPTZ NULL,

  CONSTRAINT fk_google_mailboxes_company_user
    FOREIGN KEY (company_id, user_id)
    REFERENCES users(company_id, user_id)
    ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_google_mailboxes_company_email
  ON google_mailboxes(company_id, email_address);

CREATE INDEX IF NOT EXISTS idx_google_mailboxes_company
  ON google_mailboxes(company_id);

CREATE TABLE IF NOT EXISTS message_incidents (
  message_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id       BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  user_id          UUID NOT NULL,

  source           TEXT NOT NULL CHECK (source IN ('slack','gmail')),
  sent_at          TIMESTAMPTZ NOT NULL,

  content_raw      JSONB NOT NULL,
  conversation_id  TEXT NULL,
  recommendation   TEXT NULL,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  CONSTRAINT fk_message_incidents_company_user
    FOREIGN KEY (company_id, user_id)
    REFERENCES users(company_id, user_id)
    ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS incident_scores (
  id                     BIGSERIAL PRIMARY KEY,
  message_id             UUID NOT NULL UNIQUE REFERENCES message_incidents(message_id) ON DELETE CASCADE,

  neutral_score          DOUBLE PRECISION NOT NULL,
  humor_sarcasm_score    DOUBLE PRECISION NOT NULL,
  stress_score           DOUBLE PRECISION NOT NULL,
  burnout_score          DOUBLE PRECISION NOT NULL,
  depression_score       DOUBLE PRECISION NOT NULL,
  harassment_score       DOUBLE PRECISION NOT NULL,
  suicidal_ideation_score DOUBLE PRECISION NOT NULL,

  predicted_category     TEXT NULL,
  predicted_severity     INT NULL,

  created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS auth_users (
  auth_user_id  BIGSERIAL PRIMARY KEY,
  company_id    BIGINT NOT NULL REFERENCES companies(company_id) ON DELETE RESTRICT,
  user_id       UUID NULL REFERENCES users(user_id) ON DELETE RESTRICT,
  email         CITEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_auth_users_company
  ON auth_users(company_id);

-- Idempotent column additions for schema migrations
ALTER TABLE companies         ADD COLUMN IF NOT EXISTS stripe_customer_id       TEXT NULL UNIQUE;
ALTER TABLE subscription_plans ADD COLUMN IF NOT EXISTS stripe_price_id_monthly TEXT NULL;
ALTER TABLE subscription_plans ADD COLUMN IF NOT EXISTS stripe_price_id_yearly  TEXT NULL;
ALTER TABLE message_incidents  ADD COLUMN IF NOT EXISTS recommendation           TEXT NULL;

"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(DDL)

    print("Tables/extension created.")

if __name__ == "__main__":
    main()