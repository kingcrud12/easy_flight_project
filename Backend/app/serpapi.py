from typing import Optional, Tuple, List

import pandas as pd
import requests
from fastapi import HTTPException

from .config import SERPAPI_KEY


def query_serpapi(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str],
    currency: str,
    max_price: Optional[int],
    sort_by: Optional[str],
):
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "currency": currency,
        "hl": "en",
        "api_key": SERPAPI_KEY,
    }
    if return_date:
        params["return_date"] = return_date
    if max_price:
        params["max_price"] = str(max_price)
    if sort_by:
        params["sort_by"] = sort_by

    resp = requests.get(url, params=params, timeout=30)
    try:
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"SerpApi error: {exc} - {resp.text[:500]}")
    return resp.json()


def extract_purchase_url_from_group(fg: dict, search_metadata: dict) -> Optional[str]:
    candidates = [
        "purchase_url",
        "purchase_link",
        "booking_url",
        "booking_link",
        "link",
        "deep_link",
        "deeplink",
        "booking_deeplink",
        "buy_link",
    ]
    for key in candidates:
        val = fg.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()

    if "booking" in fg and isinstance(fg["booking"], dict):
        for key in ("url", "link", "booking_url"):
            value = fg["booking"].get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    if "booking_urls" in fg and isinstance(fg["booking_urls"], list) and fg["booking_urls"]:
        first = fg["booking_urls"][0]
        if isinstance(first, str) and first.strip():
            return first.strip()
        if isinstance(first, dict):
            for key in ("url", "link"):
                value = first.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

    if isinstance(search_metadata, dict):
        google_url = search_metadata.get("google_flights_url")
        if isinstance(google_url, str) and google_url.strip():
            return google_url.strip()

    return None


def build_offers_from_response(data: dict, max_price_client: Optional[int], currency: str) -> List[dict]:
    rows: List[dict] = []
    groups = data.get("best_flights", []) + data.get("other_flights", [])
    search_metadata = data.get("search_metadata", {})

    for fg in groups:
        price = fg.get("price")
        try:
            price_val = float(price) if price is not None else None
        except Exception:
            try:
                price_val = float(str(price).replace("\u00A0", "").replace(",", "").strip())
            except Exception:
                price_val = None

        if price_val is None:
            continue
        if max_price_client is not None and price_val > max_price_client:
            continue

        total_duration = fg.get("total_duration")
        flight_type = fg.get("type")
        airline_logo = fg.get("airline_logo")
        departure_token = fg.get("departure_token")

        segments = fg.get("flights", [])
        seg_summary_list = []
        airlines_set = []
        for seg in segments:
            dep = seg.get("departure_airport", {})
            arr = seg.get("arrival_airport", {})
            dep_code = dep.get("id") or dep.get("name") or ""
            arr_code = arr.get("id") or arr.get("name") or ""
            dep_time = dep.get("time") or ""
            arr_time = arr.get("time") or ""
            airline = seg.get("airline") or ""
            airlines_set.append(airline)
            seg_summary = f"{dep_code}->{arr_code} {dep_time}→{arr_time} ({airline})"
            seg_summary_list.append(seg_summary)

        stops = max(0, len(segments) - 1)
        airlines = ", ".join([a for a in dict.fromkeys(airlines_set) if a])
        segments_text = " | ".join(seg_summary_list)
        price_insights = fg.get("price_insights", {})
        lowest_price = price_insights.get("lowest_price") if price_insights else None

        purchase_url = extract_purchase_url_from_group(fg, search_metadata)

        rows.append(
            {
                "price": price_val,
                "currency": currency,
                "airlines": airlines,
                "stops": stops,
                "total_duration_min": total_duration,
                "segments_summary": segments_text,
                "type": flight_type,
                "airline_logo": airline_logo,
                "departure_token": departure_token,
                "lowest_price_insight": lowest_price,
                "purchase_url": purchase_url,
            }
        )
    return rows


def search_offers(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str],
    currency: str,
    max_price: Optional[int],
    sort_by: Optional[str],
    top_n: int,
) -> Tuple[List[dict], int]:
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not configured on server")

    data = query_serpapi(departure_id, arrival_id, outbound_date, return_date, currency, max_price, sort_by)
    rows = build_offers_from_response(data, max_price, currency)
    df = pd.DataFrame(rows)
    if df.empty:
        return [], 0
    df_sorted = df.sort_values("price", ascending=True).reset_index(drop=True)
    df_limited = df_sorted.head(top_n)
    return df_limited.to_dict(orient="records"), len(df_limited)

