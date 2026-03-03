import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;

-- At most one ACTIVE biller per company
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_biller_per_company
ON saas_company_roles (company_id)
WHERE role = 'biller' AND status = 'active';

-- Prevent removing/deactivating the LAST active biller
CREATE OR REPLACE FUNCTION prevent_last_active_biller_removal()
RETURNS trigger AS $$
DECLARE
  remaining_active_billers int;
BEGIN
  -- Allow normal changes that do not remove an active biller
  IF TG_OP = 'DELETE' THEN
    IF OLD.role = 'biller' AND OLD.status = 'active' THEN
      SELECT count(*) INTO remaining_active_billers
      FROM saas_company_roles
      WHERE company_id = OLD.company_id
        AND role = 'biller'
        AND status = 'active'
        AND user_id <> OLD.user_id;

      IF remaining_active_billers = 0 THEN
        RAISE EXCEPTION 'Company % must have at least one active biller', OLD.company_id;
      END IF;
    END IF;
    RETURN OLD;
  END IF;

  IF TG_OP = 'UPDATE' THEN
    -- Only block if we are turning an ACTIVE biller into NOT active biller
    IF OLD.role = 'biller' AND OLD.status = 'active'
       AND (NEW.status IS DISTINCT FROM 'active' OR NEW.role IS DISTINCT FROM 'biller') THEN

      SELECT count(*) INTO remaining_active_billers
      FROM saas_company_roles
      WHERE company_id = OLD.company_id
        AND role = 'biller'
        AND status = 'active'
        AND user_id <> OLD.user_id;

      IF remaining_active_billers = 0 THEN
        RAISE EXCEPTION 'Company % must have at least one active biller', OLD.company_id;
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_last_active_biller_removal ON saas_company_roles;

CREATE TRIGGER trg_prevent_last_active_biller_removal
BEFORE UPDATE OR DELETE ON saas_company_roles
FOR EACH ROW
EXECUTE FUNCTION prevent_last_active_biller_removal();

-- At most one ACTIVE admin per company
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_admin_per_company
ON saas_company_roles (company_id)
WHERE role = 'admin' AND status = 'active';

--  Prevent removing/deactivating the LAST active admin
CREATE OR REPLACE FUNCTION prevent_last_active_admin_removal()
RETURNS trigger AS $$
DECLARE
  remaining_active_admins int;
BEGIN
  -- DELETE case
  IF TG_OP = 'DELETE' THEN
    IF OLD.role = 'admin' AND OLD.status = 'active' THEN
      SELECT count(*) INTO remaining_active_admins
      FROM saas_company_roles
      WHERE company_id = OLD.company_id
        AND role = 'admin'
        AND status = 'active'
        AND user_id <> OLD.user_id;

      IF remaining_active_admins = 0 THEN
        RAISE EXCEPTION 'Company % must have at least one active admin', OLD.company_id;
      END IF;
    END IF;
    RETURN OLD;
  END IF;

  -- UPDATE case: active admin -> not active admin
  IF TG_OP = 'UPDATE' THEN
    IF OLD.role = 'admin' AND OLD.status = 'active'
       AND (NEW.status IS DISTINCT FROM 'active' OR NEW.role IS DISTINCT FROM 'admin') THEN

      SELECT count(*) INTO remaining_active_admins
      FROM saas_company_roles
      WHERE company_id = OLD.company_id
        AND role = 'admin'
        AND status = 'active'
        AND user_id <> OLD.user_id;

      IF remaining_active_admins = 0 THEN
        RAISE EXCEPTION 'Company % must have at least one active admin', OLD.company_id;
      END IF;
    END IF;

    RETURN NEW;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_prevent_last_active_admin_removal ON saas_company_roles;

CREATE TRIGGER trg_prevent_last_active_admin_removal
BEFORE UPDATE OR DELETE ON saas_company_roles
FOR EACH ROW
EXECUTE FUNCTION prevent_last_active_admin_removal();


COMMIT;
"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Migration applied: enforced exactly one active biller + admin per company (indexes + triggers).")
if __name__ == "__main__":
    main()

    