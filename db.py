import sqlite3
import time
from contextlib import contextmanager

DB_PATH = "bot_data.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            current_model TEXT DEFAULT 'auto',
            created_at REAL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            model_used TEXT,
            ts REAL
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS exhausted (
            key_hash TEXT,
            model TEXT,
            cooldown_until REAL,
            PRIMARY KEY (key_hash, model)
        )""")
        conn.commit()


def ensure_user(user_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (user_id, current_model, created_at) VALUES (?,?,?)",
            (user_id, "auto", time.time()),
        )
        conn.commit()


def set_user_model(user_id, model_name):
    with get_conn() as conn:
        conn.execute("UPDATE users SET current_model=? WHERE user_id=?", (model_name, user_id))
        conn.commit()


def get_user_model(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT current_model FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row[0] if row else "auto"


def add_message(user_id, role, content, model_used=None):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (user_id, role, content, model_used, ts) VALUES (?,?,?,?,?)",
            (user_id, role, content, model_used, time.time()),
        )
        conn.commit()


def get_history(user_id, limit=20):
    """Returns the last `limit` messages in chronological order, ready to hand to any model."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def get_last_model_used(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT model_used FROM messages WHERE user_id=? AND role='assistant' "
            "ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
    return row[0] if row and row[0] else None


def clear_history(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        conn.commit()


def mark_exhausted(key_hash, model, cooldown_seconds):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO exhausted (key_hash, model, cooldown_until) VALUES (?,?,?)",
            (key_hash, model, time.time() + cooldown_seconds),
        )
        conn.commit()


def is_exhausted(key_hash, model):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT cooldown_until FROM exhausted WHERE key_hash=? AND model=?",
            (key_hash, model),
        ).fetchone()
    if not row:
        return False
    return time.time() < row[0]
