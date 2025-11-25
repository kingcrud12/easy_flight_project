from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import router

app = FastAPI(title="Flight Comparator API (SerpApi)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adapter pour la production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
