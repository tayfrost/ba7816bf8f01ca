import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_admin_per_company
ON saas_company_roles (company_id)
WHERE role = 'admin' AND status = 'active';

COMMIT;
"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Migration applied: enforced one active admin per company (partial unique index).")

if __name__ == "__main__":
    main()