from datetime import datetime
from typing import List, Optional

import requests

from fastapi import HTTPException

from .config import AVIATIONSTACK_KEY


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        # datetime.fromisoformat handles offsets like +00:00
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _estimate_price(duration_minutes: Optional[int], stops: int) -> float:
    # Aviationstack ne fournit pas les tarifs, on dérive une estimation basique
    if duration_minutes is None:
        duration_minutes = 90
    hours = max(1, duration_minutes / 60)
    base = 60
    return round(base + hours * 40 + stops * 30, 2)


def search_aviationstack_offers(
    departure_id: str,
    arrival_id: str,
    outbound_date: Optional[str],
    currency: str,
    max_price: Optional[int],
    top_n: int,
) -> List[dict]:
    if not AVIATIONSTACK_KEY:
        return []

    params = {
        "access_key": AVIATIONSTACK_KEY,
        "dep_iata": departure_id,
        "arr_iata": arrival_id,
        "limit": min(top_n * 2, 50),
        "flight_status": "scheduled",
    }
    if outbound_date:
        params["flight_date"] = outbound_date

    try:
        resp = requests.get("http://api.aviationstack.com/v1/flights", params=params, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Aviationstack error: {exc}")

    payload = resp.json()
    flights = payload.get("data", [])
    offers: List[dict] = []

    for flight in flights:
        dep = flight.get("departure", {})
        arr = flight.get("arrival", {})
        airline = flight.get("airline", {})
        departure_time = _parse_iso(dep.get("scheduled"))
        arrival_time = _parse_iso(arr.get("scheduled"))
        duration_minutes = None
        if departure_time and arrival_time:
            duration_minutes = max(0, int((arrival_time - departure_time).total_seconds() / 60))

        price = _estimate_price(duration_minutes, stops=0)
        if max_price is not None and price > max_price:
            continue

        segments = f"{dep.get('iata') or dep.get('airport')} → {arr.get('iata') or arr.get('airport')}"
        flight_number = flight.get("flight", {}).get("iata") or flight.get("flight", {}).get("number")
        if flight_number:
            segments = f"{segments} ({flight_number})"

        offers.append(
            {
                "price": price,
                "currency": currency.upper(),
                "airlines": airline.get("name"),
                "stops": 0,
                "total_duration_min": duration_minutes,
                "segments_summary": segments,
                "type": flight.get("flight_status"),
                "airline_logo": None,
                "departure_token": None,
                "lowest_price_insight": None,
                "purchase_url": f"https://www.google.com/travel/flights?hl=fr#flt={departure_id}.{arrival_id}",
                "source": "aviationstack",
            }
        )

        if len(offers) >= top_n:
            break

    return offers

