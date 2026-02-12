import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS subscription_plan (
    plan_id BIGSERIAL PRIMARY KEY,
    plan_name TEXT NOT NULL UNIQUE CHECK (char_length(trim(plan_name)) > 1),
    plan_cost_pennies BIGINT NOT NULL CHECK (plan_cost_pennies >= 0),
    currency CHAR(3) NOT NULL DEFAULT 'GBP',
    max_employees BIGINT NOT NULL CHECK (max_employees > 0)
);

CREATE TABLE IF NOT EXISTS companies(
    company_id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES subscription_plan(plan_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    company_name TEXT NOT NULL CHECK (char_length(trim(company_name)) > 1),
    deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS saas_user_data(
    user_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL CHECK (char_length(trim(name)) > 1),
    surname TEXT NOT NULL CHECK (char_length(trim(surname)) > 1),
    email TEXT NOT NULL UNIQUE CHECK (
                                        char_length(trim(email)) > 3
                                        AND position('@' in trim(email)) > 1
                                        AND position('@' in trim(email)) < char_length(trim(email))),
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saas_company_roles(
    company_id BIGINT NOT NULL REFERENCES companies(company_id),
    user_id BIGINT NOT NULL REFERENCES saas_user_data(user_id),
    role TEXT NOT NULL CHECK (role IN ('admin','viewer','biller')),
    status TEXT NOT NULL CHECK (status IN ('active','inactive','removed')),
    PRIMARY KEY (company_id, user_id, role)
);

CREATE TABLE IF NOT EXISTS slack_workspaces(
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(company_id),
    slack_team_id TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS slack_tracker(
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES companies(company_id),
    slack_team_id TEXT NOT NULL REFERENCES slack_workspaces(slack_team_id),
    slack_user_id TEXT NOT NULL,
    name TEXT NOT NULL CHECK (char_length(trim(name)) > 1),
    surname TEXT NOT NULL CHECK (char_length(trim(surname)) > 1),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL CHECK (status IN ('active','inactive','removed')),
    UNIQUE (slack_team_id, slack_user_id)
);
"""

def main():
    # autocommit is helpful for CREATE EXTENSION
    with psycopg.connect(DB_URL) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(DDL)

    print("Tables/extension created (or already existed).")

if __name__ == "__main__":
    main()