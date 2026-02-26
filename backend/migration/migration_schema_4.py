import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;

-- Drop old row-level triggers (if they exist)
DROP TRIGGER IF EXISTS trg_prevent_last_active_admin_removal ON saas_company_roles;
DROP TRIGGER IF EXISTS trg_prevent_last_active_biller_removal ON saas_company_roles;

-- Drop the constraint triggers too if re-running migration
DROP TRIGGER IF EXISTS trg_company_must_have_active_admin ON saas_company_roles;
DROP TRIGGER IF EXISTS trg_company_must_have_active_biller ON saas_company_roles;

-- Function: check company has at least one active admin (final state, deferred)
CREATE OR REPLACE FUNCTION ensure_company_has_active_admin()
RETURNS trigger AS $$
DECLARE
  cid bigint;
  remaining int;
BEGIN
  -- Only care if we are removing/deactivating/changing away from an ACTIVE admin row
  IF TG_OP = 'DELETE' THEN
    IF OLD.role <> 'admin' OR OLD.status <> 'active' THEN
      RETURN NULL;
    END IF;
    cid := OLD.company_id;
  ELSIF TG_OP = 'UPDATE' THEN
    -- If it was not an active admin before, nothing to enforce
    IF OLD.role <> 'admin' OR OLD.status <> 'active' THEN
      RETURN NULL;
    END IF;

    -- If it is still an active admin after, nothing to enforce
    IF NEW.role = 'admin' AND NEW.status = 'active' THEN
      RETURN NULL;
    END IF;

    cid := OLD.company_id;
  ELSE
    RETURN NULL;
  END IF;

  SELECT count(*) INTO remaining
  FROM saas_company_roles
  WHERE company_id = cid
    AND role = 'admin'
    AND status = 'active';

  IF remaining = 0 THEN
    RAISE EXCEPTION 'Company % must have at least one active admin', cid;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- Function: check company has at least one active biller (final state, deferred)
CREATE OR REPLACE FUNCTION ensure_company_has_active_biller()
RETURNS trigger AS $$
DECLARE
  cid bigint;
  remaining int;
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.role <> 'biller' OR OLD.status <> 'active' THEN
      RETURN NULL;
    END IF;
    cid := OLD.company_id;
  ELSIF TG_OP = 'UPDATE' THEN
    IF OLD.role <> 'biller' OR OLD.status <> 'active' THEN
      RETURN NULL;
    END IF;

    IF NEW.role = 'biller' AND NEW.status = 'active' THEN
      RETURN NULL;
    END IF;

    cid := OLD.company_id;
  ELSE
    RETURN NULL;
  END IF;

  SELECT count(*) INTO remaining
  FROM saas_company_roles
  WHERE company_id = cid
    AND role = 'biller'
    AND status = 'active';

  IF remaining = 0 THEN
    RAISE EXCEPTION 'Company % must have at least one active biller', cid;
  END IF;

  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- DEFERRABLE constraint triggers: checked at COMMIT (deferred)
CREATE CONSTRAINT TRIGGER trg_company_must_have_active_admin
AFTER UPDATE OR DELETE ON saas_company_roles
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ensure_company_has_active_admin();

CREATE CONSTRAINT TRIGGER trg_company_must_have_active_biller
AFTER UPDATE OR DELETE ON saas_company_roles
DEFERRABLE INITIALLY DEFERRED
FOR EACH ROW
EXECUTE FUNCTION ensure_company_has_active_biller();

COMMIT;
"""


def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Migration applied: enforced one active admin per company (partial unique index). checking at the END")

if __name__ == "__main__":
    main()