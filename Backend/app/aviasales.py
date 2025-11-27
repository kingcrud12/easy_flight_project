from datetime import datetime
from typing import List, Optional

import requests

from fastapi import HTTPException

from .config import AVIASALES_TOKEN

API_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"
AFFILIATE_LINK = "https://www.aviasales.com/search"


def _format_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    # Aviasales attend YYYY-MM-DD
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        return None


def search_aviasales_offers(
    departure_id: str,
    arrival_id: str,
    outbound_date: Optional[str],
    return_date: Optional[str],
    currency: str,
    max_price: Optional[int],
    top_n: int,
) -> List[dict]:
    if not AVIASALES_TOKEN:
        return []

    params = {
        "origin": departure_id,
        "destination": arrival_id,
        "currency": currency,
        "limit": min(top_n, 50),
    }
    dep = _format_date(outbound_date)
    ret = _format_date(return_date)
    if dep:
        params["departure_at"] = dep
    if ret:
        params["return_at"] = ret

    headers = {"X-Access-Token": AVIASALES_TOKEN}

    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Aviasales error: {exc}")

    payload = resp.json()
    data = payload.get("data", [])
    offers: List[dict] = []

    for raw in data:
        price = raw.get("price")
        if price is None:
            continue
        if max_price is not None and price > max_price:
            continue

        airlines = raw.get("airline")
        segments_summary = f"{raw.get('origin')} → {raw.get('destination')}"
        departure_at = raw.get("departure_at")
        return_at = raw.get("return_at")
        if departure_at:
            try:
                dep_dt = datetime.fromisoformat(departure_at.replace("Z", "+00:00"))
                segments_summary += f" ({dep_dt.strftime('%d %b %H:%M')})"
            except ValueError:
                pass
        if return_at:
            try:
                ret_dt = datetime.fromisoformat(return_at.replace("Z", "+00:00"))
                segments_summary += f" / Retour {ret_dt.strftime('%d %b %H:%M')}"
            except ValueError:
                pass

        stops = raw.get("transfers", 0)
        duration = raw.get("duration") or {}
        total_duration = duration.get("total")

        link = raw.get("link") or AFFILIATE_LINK

        offers.append(
            {
                "price": float(price),
                "currency": currency.upper(),
                "airlines": airlines,
                "stops": stops,
                "total_duration_min": total_duration,
                "segments_summary": segments_summary,
                "type": "aviasales",
                "airline_logo": None,
                "departure_token": None,
                "lowest_price_insight": None,
                "purchase_url": link,
                "source": "aviasales",
            }
        )

        if len(offers) >= top_n:
            break

    return offers

