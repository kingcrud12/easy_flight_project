import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import router

app = FastAPI(title="Flight Comparator API (SerpApi)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://easy-flight-project-1.onrender.com"],  # Adapter pour la production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)), reload=True)

