import uuid
from datetime import datetime
from typing import Optional, Dict, Tuple

from .config import search_tracking, FREE_SEARCH_LIMIT
from .database import get_user_by_token, update_user_fields


def get_or_create_session_id(session_id: Optional[str]) -> str:
    return session_id or str(uuid.uuid4())


def get_user_from_token(token: Optional[str]) -> Optional[Dict]:
    return get_user_by_token(token)


def check_session_quota(session_id: str) -> Tuple[bool, int]:
    data = search_tracking[session_id]
    now = datetime.now()
    if (now - data["last_reset"]).days >= 30:
        data["count"] = 0
        data["last_reset"] = now
    if data["subscription_active"]:
        return True, -1
    remaining = max(0, FREE_SEARCH_LIMIT - data["count"])
    return remaining > 0, remaining


def check_user_quota(user: Dict) -> Tuple[bool, int]:
    now = datetime.now()
    last_reset_str = user.get("last_reset")
    last_reset = datetime.fromisoformat(last_reset_str) if last_reset_str else now
    if (now - last_reset).days >= 30:
        user["free_count"] = 0
        user["last_reset"] = now.isoformat()
        update_user_fields(user["email"], free_count=0, last_reset=user["last_reset"])
    if user["subscription_active"]:
        return True, -1
    remaining = max(0, FREE_SEARCH_LIMIT - user["free_count"])
    return remaining > 0, remaining


def increment_search_counter(session_id: str, user: Optional[Dict]):
    if user:
        if not user["subscription_active"]:
            user["free_count"] += 1
            update_user_fields(user["email"], free_count=user["free_count"])
        return
    data = search_tracking[session_id]
    if not data["subscription_active"]:
        data["count"] += 1

