# backend/database.py
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
import os
from supabase import create_client, Client

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"

if load_dotenv:
    load_dotenv(dotenv_path=ENV_PATH)
else:
    print("⚠️ python-dotenv non installé. Installez-le avec `pip install python-dotenv`.")

SUPABASE_URL =  os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def row_to_user(row: Optional[Dict]) -> Optional[Dict]:
    if not row:
        return None
    return {
        "email": row["email"],
        "token": row["token"],
        "subscription_active": row["subscription_active"],
        "free_count": row["free_count"],
        "last_reset": row["last_reset"],
        "stripe_customer_id": row.get("stripe_customer_id"),
    }


def get_user_by_email(email: str) -> Optional[Dict]:
    res = supabase.table("users").select("*").eq("email", email).execute()
    if res.data:
        return row_to_user(res.data[0])
    return None


def get_user_from_token(token: Optional[str]) -> Optional[Dict]:
    if not token:
        return None
    res = supabase.table("users").select("*").eq("token", token).execute()
    if res.data:
        return row_to_user(res.data[0])
    return None


def create_user(email: str) -> Dict:
    token = str(uuid.uuid4())
    now_iso = datetime.utcnow().isoformat()
    user_data = {
        "email": email,
        "token": token,
        "subscription_active": False,
        "free_count": 0,
        "last_reset": now_iso,
    }
    res = supabase.table("users").insert(user_data).execute()
    return row_to_user(res.data[0])


def update_user_fields(email: str, **fields) -> None:
    if not fields:
        return
    supabase.table("users").update(fields).eq("email", email).execute()


def get_user_by_customer_id(customer_id: Optional[str]) -> Optional[Dict]:
    if not customer_id:
        return None
    res = supabase.table("users").select("*").eq("stripe_customer_id", customer_id).execute()
    if res.data:
        return row_to_user(res.data[0])
    return None
