import os
from pathlib import Path

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
AVIATIONSTACK_KEY = os.getenv("AVIATIONSTACK_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:63342")
PORT = int(os.getenv("PORT", "8000"))

print("🔍 Variables d'environnement chargées:")
print(f"  SERPAPI_KEY: {'✅ défini' if SERPAPI_KEY else '❌ non défini'}")
print(f"  AVIATIONSTACK_KEY: {'✅ défini' if AVIATIONSTACK_KEY else '❌ non défini'}")
print(f"  FRONTEND_URL: {FRONTEND_URL}")
