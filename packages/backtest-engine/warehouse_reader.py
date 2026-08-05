"""
Sprint 4 — Chargement de données OHLCV depuis l'entrepôt Parquet pour le
moteur de backtest.

Point d'entrée réseau/disque UNIQUE entre le moteur et l'entrepôt : ni
engine_vectorized.py, ni indicators.py, ni strategies.py ne touchent jamais
directement à un chemin de fichier — conforme au principe "non négociable"
du brief (le moteur ne lit que l'entrepôt, jamais les APIs).

Note : `_sanitize_symbol` duplique volontairement la fonction du même nom
dans packages/data-pipeline/parquet_writer.py plutôt que de faire un import
inter-packages fragile (dossiers à trait d'union, pas de package installable
pour l'instant). Si l'un des deux change, penser à répercuter sur l'autre —
à consolider dans un module partagé si ça devient gênant.
"""
import os
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))


def _sanitize_symbol(symbol: str) -> str:
    return symbol.replace("^", "IDX_").replace("=", "_").replace("/", "-")


def load_ohlcv(
    symbol: str,
    asset_class: str,
    timeframe: str = "1d",
    start: str = None,
    end: str = None,
) -> pd.DataFrame:
    """
    Charge l'historique OHLCV d'un symbole depuis l'entrepôt Parquet.

    Retourne un DataFrame trié par timestamp, index RangeIndex (0..n-1),
    colonnes : timestamp, open, high, low, close, volume.

    Lève FileNotFoundError si le symbole n'est pas dans l'entrepôt (lancer le
    script d'ingestion correspondant d'abord — voir check_warehouse_health.py
    dans packages/data-pipeline/ pour un état des lieux).
    """
    safe_symbol = _sanitize_symbol(symbol)
    base = WAREHOUSE_DIR / asset_class / safe_symbol / timeframe
    if not base.exists():
        raise FileNotFoundError(
            f"Aucune donnée pour {symbol} ({asset_class}, {timeframe}) dans "
            f"l'entrepôt. Lancer le script d'ingestion correspondant d'abord."
        )

    glob_pattern = (base / "*.parquet").as_posix()
    con = duckdb.connect()
    try:
        conditions, params = [], []
        if start:
            conditions.append("timestamp >= ?")
            params.append(start)
        if end:
            conditions.append("timestamp <= ?")
            params.append(end)
        where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
        query = (
            f"SELECT timestamp, open, high, low, close, volume "
            f"FROM read_parquet('{glob_pattern}'){where} ORDER BY timestamp"
        )
        df = con.execute(query, params).df()
    finally:
        con.close()

    if df.empty:
        raise FileNotFoundError(f"Entrepôt vide pour {symbol} sur la plage demandée.")

    return df.reset_index(drop=True)