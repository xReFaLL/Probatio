"""
Probatio API — point d'entrée FastAPI.

Sprint 0 : squelette minimal avec endpoint de santé.
Les routes métier (instruments, backtests, résultats) arrivent au Sprint 5.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Probatio API",
    description="API de backtest de stratégies de trading — sources de données gratuites uniquement.",
    version="0.0.1",
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
