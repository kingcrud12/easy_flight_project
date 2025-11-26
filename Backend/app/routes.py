from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .config import SERPAPI_KEY
from .serpapi import search_offers

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

    results, count = search_offers(
        departure_id, arrival_id, outbound_date, return_date, currency, max_price, sort_by, top_n
    )
    return {"results": results, "count": count}

