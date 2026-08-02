"""
Sprint 5 — Liste des instruments disponibles pour le backtest.

Croise l'univers statique (packages/data-pipeline/universe.py) avec ce qui
est réellement présent dans l'entrepôt Parquet, pour ne jamais proposer au
frontend un symbole sans données (le backtest échouerait sinon avec un 404).
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))

from dotenv import load_dotenv  # noqa: E402
from fastapi import APIRouter  # noqa: E402

from parquet_writer import _sanitize_symbol  # noqa: E402
from universe import CAC40, COMMODITIES, CRYPTO_PAIRS, FOREX_PAIRS, INDICES, SP500  # noqa: E402

from .schemas import InstrumentOut  # noqa: E402

load_dotenv()
WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))

_STATIC_UNIVERSE = {
    "equity": [(s, n) for s, n in SP500] + [(s, n) for s, n in CAC40],
    "index": [(s, n) for s, n in INDICES],
    "forex": [(s, n) for s, n in FOREX_PAIRS],
    "commodity": [(s, n) for s, n in COMMODITIES],
    "crypto": [(s, s) for s in CRYPTO_PAIRS],
}

router = APIRouter()


def list_available_instruments(timeframe: str = "1d") -> list[dict]:
    """Ne retourne que les instruments pour lesquels un dossier de données
    existe vraiment dans l'entrepôt (pas juste une entrée dans l'univers
    statique — celui-ci liste tout ce qui *devrait* être ingéré, pas ce qui
    l'est réellement)."""
    available = []
    for asset_class, entries in _STATIC_UNIVERSE.items():
        for symbol, name in entries:
            safe_symbol = _sanitize_symbol(symbol)
            if (WAREHOUSE_DIR / asset_class / safe_symbol / timeframe).exists():
                available.append({"symbol": symbol, "name": name, "asset_class": asset_class})
    return available


@router.get("/instruments", response_model=list[InstrumentOut])
def get_instruments():
    return list_available_instruments()