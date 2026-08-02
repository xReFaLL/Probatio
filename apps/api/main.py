"""
Probatio API — point d'entrée FastAPI.

Sprint 5 : routes métier (instruments, backtests) branchées sur le moteur
Sprint 4 et l'entrepôt. Toute la logique vit dans instruments.py / backtests.py
/ db.py — ce fichier ne fait qu'assembler l'application.
"""
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI(
    title="Probatio API",
    description="API de backtest de stratégies de trading — sources de données gratuites uniquement.",
    version="0.1.0",
)

origins = os.getenv("API_CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "probatio-api"}


@app.get("/")
def root():
    return {"message": "Probatio API — voir /docs pour la documentation OpenAPI"}


from .backtests import router as backtests_router  # noqa: E402
from .instruments import router as instruments_router  # noqa: E402

app.include_router(instruments_router, prefix="/api", tags=["instruments"])
app.include_router(backtests_router, prefix="/api", tags=["backtests"])