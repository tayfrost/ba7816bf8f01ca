import os
from sqlalchemy import create_engine, text

DB_URL = os.environ["DATABASE_URL_SYNC"]

def run():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE google_mailboxes
            ALTER COLUMN last_history_id TYPE TEXT
            USING last_history_id::TEXT
        """))
    print("Updated google_mailboxes.last_history_id to TEXT")

if __name__ == "__main__":
    run()