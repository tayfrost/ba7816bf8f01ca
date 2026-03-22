import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sentinelai"

MIGRATION = """
BEGIN;

CREATE TABLE IF NOT EXISTS message_details (
    id BIGSERIAL PRIMARY KEY,

    incident_id BIGINT NOT NULL
        REFERENCES flagged_incidents(incident_id)
        ON DELETE CASCADE,

    team_id TEXT NOT NULL,
    slack_user_id TEXT NOT NULL,

    -- mental directions from CATEGORY_MAP
    neutral_score REAL NOT NULL,
    humor_sarcasm_score REAL NOT NULL,
    stress_score REAL NOT NULL,
    burnout_score REAL NOT NULL,
    depression_score REAL NOT NULL,
    harassment_score REAL NOT NULL,
    suicidal_ideation_score REAL NOT NULL,

    -- predicted labels
    predicted_category SMALLINT,
    predicted_severity SMALLINT,

    -- ensure 1 scoring row per incident 
    CONSTRAINT uq_message_details_incident UNIQUE (incident_id),

    -- ensure the (team_id, slack_user_id) pair is valid
    CONSTRAINT fk_message_details_user
        FOREIGN KEY (team_id, slack_user_id)
        REFERENCES slack_users (team_id, slack_user_id)
);

-- Useful index: scores over time per employee 
CREATE INDEX IF NOT EXISTS idx_message_details_team_user
    ON message_details (team_id, slack_user_id);

COMMIT;
"""

def main():
    with psycopg.connect(DB_URL) as conn:
        conn.execute(MIGRATION)
    print("Created new table message_details")

if __name__ == "__main__":
    main()