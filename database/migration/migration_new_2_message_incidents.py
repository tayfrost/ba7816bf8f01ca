import os
from sqlalchemy import create_engine, text

DB_URL = os.environ["DATABASE_URL_SYNC"]

def run():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE message_incidents
            ADD COLUMN IF NOT EXISTS recommendation TEXT;
        """))
    print("Added recommendation column to message_incidents")

if __name__ == "__main__":
    run()