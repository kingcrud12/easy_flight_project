from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query, Header, Request
from pydantic import BaseModel

from .config import (
    SERPAPI_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_ID,
    STRIPE_WEBHOOK_SECRET,
    FRONTEND_URL,
    FREE_SEARCH_LIMIT,
    search_tracking,
    stripe,
)
from .serpapi import search_offers
from .quota import (
    get_or_create_session_id,
    get_user_from_token,
    check_user_quota,
    check_session_quota,
    increment_search_counter,
)
from .database import (
    get_user_by_email,
    create_user,
    update_user_fields,
    get_user_by_customer_id,
)
from .mailer import send_subscription_confirmation

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


class CheckoutSessionRequest(BaseModel):
    email: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class PriceResponse(BaseModel):
    amount: int
    currency: str
    formatted: str


class SearchQuotaResponse(BaseModel):
    remaining: int
    limit: int
    subscription_active: bool
    requires_login: bool = False
    email: Optional[str] = None


class LoginRequest(BaseModel):
    email: str


class LoginResponse(BaseModel):
    token: str
    email: str
    subscription_active: bool
    remaining: int
    limit: int


def normalize_email(email: str) -> str:
    return email.strip().lower()


@router.get("/search", response_model=SearchResponse)
def search_flights(
    departure_id: str = Query(..., description="IATA code depart, e.g. CDG"),
    arrival_id: str = Query(..., description="IATA code arrivée, e.g. LON or LHR"),
    outbound_date: str = Query(..., description="YYYY-MM-DD"),
    return_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    currency: str = Query("USD"),
    max_price: Optional[int] = Query(None, description="Max price client-side filter (int)"),
    sort_by: Optional[str] = Query(None, description="SerpApi sort_by"),
    top_n: int = Query(10, ge=1, le=100),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
):
    if not SERPAPI_KEY:
        raise HTTPException(status_code=500, detail="SERPAPI_KEY not configured on server")

    session_id = get_or_create_session_id(x_session_id)
    user = get_user_from_token(x_user_token)
    if user:
        allowed, _ = check_user_quota(user)
    else:
        allowed, _ = check_session_quota(session_id)

    if not allowed:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "quota_exceeded",
                "message": "Limite gratuite atteinte. Connectez-vous ou abonnez-vous pour continuer.",
                "requires_login": user is None,
            },
        )

    results, count = search_offers(
        departure_id, arrival_id, outbound_date, return_date, currency, max_price, sort_by, top_n
    )

    increment_search_counter(session_id, user)
    return {"results": results, "count": count}


@router.post("/auth/login", response_model=LoginResponse)
def login_user(payload: LoginRequest):
    email = normalize_email(payload.email)
    if not email:
        raise HTTPException(status_code=400, detail="Email invalide")

    user = get_user_by_email(email)
    if not user:
        user = create_user(email)

    _, remaining = check_user_quota(user)
    return LoginResponse(
        token=user["token"],
        email=email,
        subscription_active=user["subscription_active"],
        remaining=remaining,
        limit=FREE_SEARCH_LIMIT,
    )


@router.get("/auth/me", response_model=LoginResponse)
def get_current_user(x_user_token: Optional[str] = Header(None, alias="X-User-Token")):
    user = get_user_from_token(x_user_token)
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non connecté")
    _, remaining = check_user_quota(user)
    return LoginResponse(
        token=user["token"],
        email=user["email"],
        subscription_active=user["subscription_active"],
        remaining=remaining,
        limit=FREE_SEARCH_LIMIT,
    )


@router.get("/billing/price", response_model=PriceResponse)
def get_subscription_price():
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key non configuré")
    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe price ID non configuré")

    try:
        price = stripe.Price.retrieve(STRIPE_PRICE_ID)
        amount = price.unit_amount or 1000
        currency = (price.currency or "eur").upper()
        formatted = f"{amount / 100:.2f} {currency}"
        return PriceResponse(amount=amount, currency=currency, formatted=formatted)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {str(exc)}")


@router.get("/billing/quota", response_model=SearchQuotaResponse)
def get_quota(
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
):
    user = get_user_from_token(x_user_token)
    if user:
        _, remaining = check_user_quota(user)
        return SearchQuotaResponse(
            remaining=remaining,
            limit=FREE_SEARCH_LIMIT,
            subscription_active=user["subscription_active"],
            requires_login=False,
            email=user["email"],
        )

    session_id = get_or_create_session_id(x_session_id)
    data = search_tracking[session_id]
    if data["subscription_active"]:
        return SearchQuotaResponse(remaining=-1, limit=-1, subscription_active=True, requires_login=False)
    remaining = max(0, FREE_SEARCH_LIMIT - data["count"])
    return SearchQuotaResponse(
        remaining=remaining,
        limit=FREE_SEARCH_LIMIT,
        subscription_active=False,
        requires_login=True,
    )


@router.post("/billing/session", response_model=CheckoutSessionResponse)
def create_checkout_session(
    payload: CheckoutSessionRequest,
    x_user_token: Optional[str] = Header(None, alias="X-User-Token"),
):
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Stripe secret key non configuré")
    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Stripe price ID non configuré")

    user = get_user_from_token(x_user_token)
    if not user:
        raise HTTPException(status_code=401, detail="Connectez-vous pour souscrire")
    if user["subscription_active"]:
        raise HTTPException(status_code=400, detail="Abonnement déjà actif")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            customer_email=user["email"],
            success_url=f"{FRONTEND_URL}/success.html?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/index.html",
            metadata={"email": user["email"], "user_token": user["token"]},
        )
        return CheckoutSessionResponse(checkout_url=session.url, session_id=session.id)
    except stripe.error.StripeError as exc:
        raise HTTPException(status_code=400, detail=f"Erreur Stripe: {str(exc)}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur inattendue: {str(exc)}")


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook non configuré")
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Payload invalide")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Signature invalide")

    event_type = event.get("type")
    data_object = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        metadata = data_object.get("metadata", {})
        user_token = metadata.get("user_token")
        if user_token:
            user = get_user_from_token(user_token)
            if user:
                now_iso = datetime.now().isoformat()
                update_user_fields(
                    user["email"],
                    subscription_active=1,
                    free_count=0,
                    last_reset=now_iso,
                    stripe_customer_id=data_object.get("customer"),
                )
                print(f"✅ Subscription activated for {user['email']}")
                amount_total = data_object.get("amount_total") or 0
                currency = (data_object.get("currency") or "eur").upper()
                start = datetime.utcnow()
                end = start + timedelta(days=365)
                send_subscription_confirmation(
                    user["email"],
                    amount=amount_total / 100,
                    currency=currency,
                    start_date=start.strftime("%d/%m/%Y"),
                    end_date=end.strftime("%d/%m/%Y"),
                    session_id=data_object.get("id"),
                )
            else:
                print(f"⚠️ user_token {user_token} introuvable en base")
    elif event_type in ("invoice.payment_failed", "customer.subscription.deleted"):
        customer_id = data_object.get("customer")
        user = get_user_by_customer_id(customer_id)
        if user:
            update_user_fields(user["email"], subscription_active=0)
            print(f"⚠️ Subscription suspended pour {user['email']} (event {event_type})")
        else:
            print(f"⚠️ Subscription issue detected pour customer={customer_id}")

    return {"status": "ok"}

