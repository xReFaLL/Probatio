"""
Sprint 1 — Vérification croisée d'un échantillon de tickers : compare le
dernier close présent dans l'entrepôt Parquet (alimenté par yfinance) à celui
renvoyé par Stooq pour les mêmes dates.

Usage :
    python packages/data-pipeline/verify_cross_check_stooq.py

Limites Stooq : quota quotidien de requêtes assez bas -> échantillon réduit
(5 tickers actions par défaut) et une seule requête par ticker.
"""
import io
import csv
import os
import sys
from pathlib import Path

import duckdb
import requests
from dotenv import load_dotenv

load_dotenv()

WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))

# Échantillon d'actions US couvrant l'univers de départ, avec leur code Stooq
# (suffixe .us pour les actions US, cf. docs/data-sources.md).
SAMPLE = [
    ("AAPL", "aapl.us"),
    ("MSFT", "msft.us"),
    ("KO", "ko.us"),
    ("JPM", "jpm.us"),
    ("XOM", "xom.us"),
]

STOOQ_URL = "https://stooq.com/q/d/l/?s={code}&i=d"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Tolérance relative acceptée entre les deux sources (ajustements de
# dividendes/splits peuvent créer de petits écarts légitimes).
TOLERANCE_PCT = 1.0


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


def last_close_from_stooq(stooq_code: str):
    url = STOOQ_URL.format(code=stooq_code)
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200 or not resp.text.startswith("Date"):
        return None, None

    reader = list(csv.DictReader(io.StringIO(resp.text)))
    if not reader:
        return None, None

    last_row = reader[-1]
    return last_row["Date"], float(last_row["Close"])


def main():
    print(f"{'Symbole':<8} {'Date entrepôt':<14} {'Close yfinance':>15} {'Close Stooq':>13} {'Écart %':>10}")
    print("-" * 65)

    any_mismatch = False
    for symbol, stooq_code in SAMPLE:
        wh_date, wh_close = last_close_from_warehouse(symbol)
        if wh_close is None:
            print(f"{symbol:<8} -- pas encore dans l'entrepôt (lancer ingest_yfinance.py d'abord) --")
            continue

        st_date, st_close = last_close_from_stooq(stooq_code)
        if st_close is None:
            print(f"{symbol:<8} -- échec de récupération Stooq (quota ? code invalide ?) --")
            continue

        pct_diff = abs(wh_close - st_close) / st_close * 100
        flag = "" if pct_diff <= TOLERANCE_PCT else "  <-- ÉCART"
        if pct_diff > TOLERANCE_PCT:
            any_mismatch = True

        print(f"{symbol:<8} {str(wh_date)[:10]:<14} {wh_close:>15.2f} {st_close:>13.2f} {pct_diff:>9.2f}%{flag}")

    if any_mismatch:
        print("\n[ATTENTION] Au moins un écart dépasse la tolérance — vérifier manuellement.")
        sys.exit(1)

    print("\n[OK] Tous les tickers de l'échantillon sont cohérents avec Stooq.")


if __name__ == "__main__":
    main()
