import sqlite3
import uuid
from datetime import datetime
from typing import Optional, Dict

from .config import BASE_DIR

DB_PATH = BASE_DIR / "billing.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            token TEXT UNIQUE,
            subscription_active INTEGER DEFAULT 0,
            free_count INTEGER DEFAULT 0,
            last_reset TEXT,
            stripe_customer_id TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def row_to_user(row: Optional[sqlite3.Row]) -> Optional[Dict]:
    if not row:
        return None
    return {
        "email": row["email"],
        "token": row["token"],
        "subscription_active": bool(row["subscription_active"]),
        "free_count": row["free_count"],
        "last_reset": row["last_reset"],
        "stripe_customer_id": row["stripe_customer_id"],
    }


def get_user_by_email(email: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row_to_user(row)


def get_user_by_token(token: Optional[str]) -> Optional[Dict]:
    if not token:
        return None
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE token = ?", (token,)).fetchone()
    conn.close()
    return row_to_user(row)


def create_user(email: str) -> Dict:
    token = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO users (email, token, subscription_active, free_count, last_reset)
        VALUES (?, ?, 0, 0, ?)
        """,
        (email, token, now_iso),
    )
    conn.commit()
    conn.close()
    return {
        "email": email,
        "token": token,
        "subscription_active": False,
        "free_count": 0,
        "last_reset": now_iso,
        "stripe_customer_id": None,
    }


def update_user_fields(email: str, **fields) -> None:
    if not fields:
        return
    columns = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values())
    values.append(email)
    conn = get_connection()
    conn.execute(f"UPDATE users SET {columns} WHERE email = ?", values)
    conn.commit()
    conn.close()


def get_user_by_customer_id(customer_id: Optional[str]) -> Optional[Dict]:
    if not customer_id:
        return None
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE stripe_customer_id = ?", (customer_id,)).fetchone()
    conn.close()
    return row_to_user(row)


init_db()

