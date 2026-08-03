"""
Probatio API — point d'entrée FastAPI.

Sprint 5 : routes métier (instruments, backtests) branchées sur le moteur
Sprint 4 et l'entrepôt.
Sprint 6 : ajoute walk-forward, screener, comparateur de strategies et
portefeuille multi-actifs -- chacun dans son propre router, meme pattern
que Sprint 5. Toute la logique vit dans les fichiers dedies (instruments.py,
backtests.py, walk_forward.py, screener.py, compare.py, portfolio.py, db.py)
-- ce fichier ne fait qu'assembler l'application.
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
from .compare import router as compare_router  # noqa: E402
from .instruments import router as instruments_router  # noqa: E402
from .portfolio import router as portfolio_router  # noqa: E402
from .screener import router as screener_router  # noqa: E402
from .walk_forward import router as walk_forward_router  # noqa: E402

app.include_router(instruments_router, prefix="/api", tags=["instruments"])
app.include_router(backtests_router, prefix="/api", tags=["backtests"])
app.include_router(walk_forward_router, prefix="/api", tags=["walk-forward"])
app.include_router(screener_router, prefix="/api", tags=["screener"])
app.include_router(compare_router, prefix="/api", tags=["compare"])
app.include_router(portfolio_router, prefix="/api", tags=["portfolio"])