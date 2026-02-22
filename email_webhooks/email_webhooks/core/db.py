import sqlite3
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

DB_FILE = "email_service.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS gmail_users (
            user_email TEXT PRIMARY KEY,
            token_json TEXT NOT NULL,
            last_history_id TEXT,
            watch_expiration_ms TEXT
        )
        """)


def upsert_gmail_user(user_email: str, token_json: str):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO gmail_users (user_email, token_json)
        VALUES (?, ?)
        ON CONFLICT(user_email) DO UPDATE SET
            token_json=excluded.token_json
        """, (user_email, token_json))


def get_gmail_user(user_email: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM gmail_users WHERE user_email=?",
            (user_email,)
        ).fetchone()
        return dict(row) if row else None


def update_user_history_id(user_email: str, last_history_id: str):
    with get_conn() as conn:
        conn.execute("""
        UPDATE gmail_users
        SET last_history_id=?
        WHERE user_email=?
        """, (last_history_id, user_email))


def update_user_watch(user_email: str, history_id: str, expiration_ms: str):
    with get_conn() as conn:
        conn.execute("""
        UPDATE gmail_users
        SET last_history_id=?, watch_expiration_ms=?
        WHERE user_email=?
        """, (history_id, expiration_ms, user_email))


def list_gmail_users() -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM gmail_users").fetchall()
        return [dict(r) for r in rows]


if __name__ == "__main__":
    init_db()
    print("DB initialized ✅")
