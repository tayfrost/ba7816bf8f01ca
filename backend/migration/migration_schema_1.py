import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;

-- slack_workspaces: rename slack_team_id -> team_id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='slack_workspaces' AND column_name='slack_team_id'
  ) THEN
    ALTER TABLE slack_workspaces RENAME COLUMN slack_team_id TO team_id;
  END IF;
END $$;

-- 2) slack_workspaces: add access_token constraint not null 
ALTER TABLE slack_workspaces
  ADD COLUMN IF NOT EXISTS access_token TEXT NOT NULL;
ALTER TABLE slack_workspaces
  ALTER COLUMN access_token SET NOT NULL;


-- Rename slack_tracker table -> slack_users
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='slack_tracker')
     AND NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='slack_users')
  THEN
    ALTER TABLE slack_tracker RENAME TO slack_users;
  END IF;
END $$;

-- Drop old constraints that might reference old names
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_tracker_slack_team_id_fkey;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_users_slack_team_id_fkey;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_users_team_id_fkey;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_tracker_company_id_fkey;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_users_company_id_fkey;

-- slack_users: rename slack_team_id -> team_id
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='slack_users' AND column_name='slack_team_id'
  ) THEN
    ALTER TABLE slack_users RENAME COLUMN slack_team_id TO team_id;
  END IF;
END $$;

-- slack_users: drop company_id
ALTER TABLE slack_users
  DROP COLUMN IF EXISTS company_id;

-- Fix UNIQUE(team_id, slack_user_id)
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS uq_tracker_team_user;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_tracker_slack_team_id_slack_user_id_key;
ALTER TABLE slack_users
  DROP CONSTRAINT IF EXISTS slack_users_team_id_slack_user_id_key;

ALTER TABLE slack_users
  ADD CONSTRAINT uq_slack_users_team_user UNIQUE (team_id, slack_user_id);

-- Recreate FK(team_id) -> slack_workspaces(team_id)
ALTER TABLE slack_users
  ADD CONSTRAINT fk_slack_users_team
  FOREIGN KEY (team_id) REFERENCES slack_workspaces(team_id)
  ON DELETE RESTRICT;

COMMIT;
"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Migration applied: workspaces team_id+access_token; slack_tracker->slack_users; drop company_id; FK+UNIQUE fixed.")

if __name__ == "__main__":
    main()