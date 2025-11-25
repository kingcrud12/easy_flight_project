import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import stripe

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

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_EK")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500/Frontend")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

PORT = int(os.getenv("PORT", "8000"))

print("🔍 Debug variables d'environnement:")
print(f"  SERPAPI_KEY: {'✅ défini' if SERPAPI_KEY else '❌ non défini'}")
print(f"  STRIPE_SECRET_EK: {'✅ défini' if STRIPE_SECRET_KEY else '❌ non défini'}")
if STRIPE_SECRET_KEY:
    print(f"    Commence par: {STRIPE_SECRET_KEY[:10]}...")
print(f"  STRIPE_PRICE_ID: {'✅ défini' if STRIPE_PRICE_ID else '❌ non défini'}")
if STRIPE_PRICE_ID:
    print(f"    Valeur: {STRIPE_PRICE_ID}")
print(f"  SMTP_USER: {'✅ défini' if SMTP_USER else '❌ non défini'}")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    print("✅ Stripe configuré avec succès")
else:
    print("⚠️ STRIPE_SECRET_EK absent : fonctionnalités Stripe désactivées.")

FREE_SEARCH_LIMIT = 2

search_tracking = defaultdict(
    lambda: {"count": 0, "subscription_active": False, "last_reset": datetime.now()}
)

