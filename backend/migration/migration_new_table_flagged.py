import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;
CREATE TABLE IF NOT EXISTS flagged_incidents (
    incident_id BIGSERIAL PRIMARY KEY,

    company_id BIGINT NOT NULL REFERENCES companies(company_id),

    team_id TEXT NOT NULL REFERENCES slack_workspaces(team_id),

    slack_user_id TEXT NOT NULL,

    message_ts TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    channel_id TEXT NOT NULL,

    raw_message_text JSONB NOT NULL,

    class_reason TEXT,

    CONSTRAINT fk_flagged_incidents_tracker
        FOREIGN KEY (team_id, slack_user_id)
        REFERENCES slack_users (team_id, slack_user_id)
);

-- extra indexes will need for ordering
CREATE INDEX IF NOT EXISTS idx_flagged_incidents_company_created_at
    ON flagged_incidents (company_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_flagged_incidents_team_user_created_at
    ON flagged_incidents (team_id, slack_user_id, created_at DESC);
    
COMMIT;    
"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Created new table flagegd_incidents.py")

if __name__ == "__main__":
    main()