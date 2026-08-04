"""
Sprint 1 (mise à jour Sprint 3) — Vérification croisée d'un échantillon de
tickers : compare le dernier close présent dans l'entrepôt Parquet (alimenté
par yfinance) à celui renvoyé par Twelve Data pour les mêmes dates.

Remplace verify_cross_check_stooq.py : Stooq bloque désormais les clients
HTTP non-navigateur via un challenge anti-bot (voir docs/data-sources.md,
Sprint 3). Twelve Data était déjà intégré comme source backup (clé API en
place) et sert aussi bien pour la vérification croisée que pour le backup —
aucune nouvelle dépendance introduite.

Usage :
    python packages/data-pipeline/verify_cross_check_twelvedata.py

Limite Twelve Data : 800 crédits/jour, 8/min — un échantillon de 5 tickers
avec une pause entre appels reste très large de la marge.
"""
import os
import sys
import time
from pathlib import Path

import duckdb
import requests
from dotenv import load_dotenv

load_dotenv()

WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))
API_KEY = os.getenv("TWELVEDATA_API_KEY")
URL = "https://api.twelvedata.com/time_series"

# Même échantillon d'actions US qu'au Sprint 1.
SAMPLE = ["AAPL", "MSFT", "KO", "JPM", "XOM"]

# Tolérance relative acceptée entre les deux sources (ajustements de
# dividendes/splits peuvent créer de petits écarts légitimes).
TOLERANCE_PCT = 1.0

# Respecte la limite 8/min de Twelve Data avec de la marge.
DELAY_BETWEEN_CALLS_SEC = 2


def last_close_from_warehouse(symbol: str):
    equity_dir = WAREHOUSE_DIR / "equity" / symbol / "1d"
    if not equity_dir.exists():
        return None, None

    parquet_files = sorted(equity_dir.glob("*.parquet"))
    if not parquet_files:
        return None, None

    latest_file = parquet_files[-1]
    con = duckdb.connect()
    try:
        row = con.execute(
            f"SELECT timestamp, close FROM read_parquet('{latest_file.as_posix()}') "
            f"ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
    finally:
        con.close()

    if row is None:
        return None, None
    return row[0], row[1]


def last_close_from_twelvedata(symbol: str):
    params = {"symbol": symbol, "interval": "1day", "outputsize": 1, "apikey": API_KEY}
    try:
        resp = requests.get(URL, params=params, timeout=10)
        payload = resp.json()
    except Exception:
        return None, None

    if payload.get("status") == "error" or "values" not in payload or not payload["values"]:
        return None, None

    last_point = payload["values"][0]
    return last_point["datetime"], float(last_point["close"])


def main():
    if not API_KEY:
        print("[ECHEC] TWELVEDATA_API_KEY absente du .env")
        sys.exit(1)

    print(f"{'Symbole':<8} {'Date entrepôt':<14} {'Close yfinance':>15} {'Close Twelve Data':>18} {'Écart %':>10}")
    print("-" * 72)

    any_mismatch = False
    for i, symbol in enumerate(SAMPLE):
        if i > 0:
            time.sleep(DELAY_BETWEEN_CALLS_SEC)

        wh_date, wh_close = last_close_from_warehouse(symbol)
        if wh_close is None:
            print(f"{symbol:<8} -- pas encore dans l'entrepôt (lancer ingest_yfinance.py d'abord) --")
            continue

        td_date, td_close = last_close_from_twelvedata(symbol)
        if td_close is None:
            print(f"{symbol:<8} -- échec de récupération Twelve Data (quota ? symbole invalide ?) --")
            continue

        pct_diff = abs(wh_close - td_close) / td_close * 100
        flag = "" if pct_diff <= TOLERANCE_PCT else "  <-- ÉCART"
        if pct_diff > TOLERANCE_PCT:
            any_mismatch = True

        print(f"{symbol:<8} {str(wh_date)[:10]:<14} {wh_close:>15.2f} {td_close:>18.2f} {pct_diff:>9.2f}%{flag}")

    if any_mismatch:
        print("\n[ATTENTION] Au moins un écart dépasse la tolérance — vérifier manuellement.")
        sys.exit(1)

    print("\n[OK] Tous les tickers de l'échantillon sont cohérents avec Twelve Data.")


if __name__ == "__main__":
    main()
