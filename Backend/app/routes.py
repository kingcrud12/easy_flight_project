from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .config import SERPAPI_KEY
from .serpapi import search_offers as search_serpapi_offers
from .aviasales import search_aviasales_offers

router = APIRouter()


class SearchResult(BaseModel):
    price: float
    currency: Optional[str]
    airlines: Optional[str]
    stops: int
    total_duration_min: Optional[int]
    segments_summary: Optional[str]
    type: Optional[str]
    airline_logo: Optional[str]
    departure_token: Optional[str]
    lowest_price_insight: Optional[float]
    purchase_url: Optional[str]
    source: Optional[str]


class SearchResponse(BaseModel):
    results: List[SearchResult]
    count: int


@router.get("/health")
def healthcheck():
    return {"status": "ok"}


@router.get("/search", response_model=SearchResponse)
def search_flights(
    departure_id: str = Query(..., description="IATA code départ, e.g. CDG"),
    arrival_id: str = Query(..., description="IATA code arrivée, e.g. LON ou LHR"),
    outbound_date: str = Query(..., description="YYYY-MM-DD"),
    return_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    currency: str = Query("USD"),
    max_price: Optional[int] = Query(None, description="Filtre prix côté client"),
    sort_by: Optional[str] = Query(None, description="Paramètre sort_by SerpApi"),
    top_n: int = Query(10, ge=1, le=100),
):
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not configured on server")

    combined: List[dict] = []

    serp_results, _ = search_serpapi_offers(
        departure_id, arrival_id, outbound_date, return_date, currency, max_price, sort_by, top_n
    )
    for result in serp_results:
        result["source"] = "serpapi"
    combined.extend(serp_results)

    try:
        aviasales_results = search_aviasales_offers(
            departure_id, arrival_id, outbound_date, return_date, currency, max_price, top_n
        )
        combined.extend(aviasales_results)
    except HTTPException as exc:
        print(f"⚠️ Aviasales error: {exc.detail}")

    if not combined:
        return {"results": [], "count": 0}

    combined.sort(key=lambda item: item.get("price") if item.get("price") is not None else float("inf"))
    limited = combined[:top_n]

    def ensure_provider(provider: str, current: List[dict]) -> List[dict]:
        if any(entry.get("source") == provider for entry in current):
            return current
        for candidate in combined:
            if candidate.get("source") == provider and candidate not in current:
                current.append(candidate)
                current.sort(key=lambda item: item.get("price") if item.get("price") is not None else float("inf"))
                return current[:top_n]
        return current

    for provider in ("serpapi", "aviasales"):
        limited = ensure_provider(provider, limited)

    return {"results": limited, "count": len(combined)}

