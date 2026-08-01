"""
Sprint 3 — Ingestion macro via FRED (Federal Reserve Economic Data), pour
l'univers de séries retenu (voir universe.MACRO_SERIES).

Usage :
    python packages/data-pipeline/ingest_fred.py
    python packages/data-pipeline/ingest_fred.py --limit 5
    python packages/data-pipeline/ingest_fred.py --series CPIAUCSL,FEDFUNDS

Choix par défaut (point non couvert par le brief) : FRED sert des séries
scalaires (une valeur par date), pas des chandeliers OHLCV. Plutôt que
d'ajouter un schéma dédié, on réutilise l'entrepôt Parquet existant : la
valeur est dupliquée dans open/high/low/close, volume=0. Ça garde un point
d'accès unique (DuckDB sur l'entrepôt) pour toutes les séries temporelles du
projet, marché comme macro, ce qui simplifie les jointures/corrélations
futures (Sprint 6). asset_class="macro".

Le timeframe de partitionnement est dérivé de la fréquence native de chaque
série FRED (mensuelle, trimestrielle, quotidienne...) via FREQUENCY_MAP,
plutôt que fixé à "1d" comme les autres pipelines — une série mensuelle
comme CPIAUCSL n'a pas de sens réinterpolée en quotidien.

Écrit dans data/warehouse/macro/{series_id}/{timeframe}/{year}.parquet via
parquet_writer.write_ohlcv (même mécanisme de déduplication/idempotence
qu'aux Sprints 1-2). Ne fait AUCUN appel direct depuis le moteur de
backtest — ce script est le seul point d'entrée réseau vers FRED.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime

import pandas as pd
import requests
from dotenv import load_dotenv

from universe import MACRO_SERIES
from parquet_writer import write_ohlcv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_fred")

API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred"
SOURCE = "fred"
SLEEP_BETWEEN_CALLS = 0.3  # limite FRED "généreuse" (brief) mais pas de raison de la stresser
MAX_RETRIES = 3
TIMEOUT = 15

# frequency_short renvoyé par FRED -> convention de timeframe du projet
FREQUENCY_MAP = {
    "d": "1d", "w": "1w", "bw": "2w", "m": "1mo",
    "q": "1q", "sa": "6mo", "a": "1y",
}


def _get(endpoint: str, params: dict) -> "dict | None":
    full_params = {**params, "api_key": API_KEY, "file_type": "json"}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(f"{BASE_URL}/{endpoint}", params=full_params, timeout=TIMEOUT)
        except Exception as e:
            log.warning("  tentative %d/%d échouée : %s", attempt, MAX_RETRIES, e)
            time.sleep(2 * attempt)
            continue

        if resp.status_code != 200:
            log.warning("  statut HTTP %d (tentative %d/%d) pour %s", resp.status_code, attempt, MAX_RETRIES, endpoint)
            time.sleep(2 * attempt)
            continue

        try:
            return resp.json()
        except ValueError:
            log.warning("  réponse non-JSON (tentative %d/%d)", attempt, MAX_RETRIES)
            time.sleep(2 * attempt)
            continue

    return None


def fetch_series(series_id: str) -> "tuple[pd.DataFrame | None, str]":
    """Récupère les métadonnées (fréquence) puis l'historique complet d'une
    série FRED. Retourne (DataFrame OHLCV-like ou None, timeframe déduit)."""
    meta = _get("series", {"series_id": series_id})
    if not meta or not meta.get("seriess"):
        return None, "1d"

    freq_short = (meta["seriess"][0].get("frequency_short") or "").lower()
    timeframe = FREQUENCY_MAP.get(freq_short, freq_short or "1d")

    obs = _get("series/observations", {"series_id": series_id, "sort_order": "asc"})
    if not obs or not obs.get("observations"):
        return None, timeframe

    df = pd.DataFrame(obs["observations"])
    if df.empty:
        return None, timeframe

    # FRED encode les valeurs manquantes par le caractère "."
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    if df.empty:
        return None, timeframe

    df["timestamp"] = pd.to_datetime(df["date"], utc=True)
    df["open"] = df["high"] = df["low"] = df["close"] = df["value"]
    df["volume"] = 0.0

    return df[["timestamp", "open", "high", "low", "close", "volume"]], timeframe


def main():
    parser = argparse.ArgumentParser(description="Ingestion macro FRED")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de séries (tests)")
    parser.add_argument("--series", type=str, default=None, help="Liste CSV d'IDs FRED, ex: CPIAUCSL,FEDFUNDS")
    args = parser.parse_args()

    if not API_KEY:
        log.error("FRED_API_KEY absente du .env — voir .env.example")
        sys.exit(1)

    series_ids = (
        [s.strip().upper() for s in args.series.split(",")]
        if args.series
        else [sid for sid, _ in MACRO_SERIES]
    )
    if args.limit:
        series_ids = series_ids[: args.limit]

    log.info("Ingestion de %d séries macro via FRED", len(series_ids))

    ok, failed = [], []
    started_at = datetime.now()

    for i, series_id in enumerate(series_ids, start=1):
        log.info("[%d/%d] %s", i, len(series_ids), series_id)
        df, timeframe = fetch_series(series_id)

        if df is None:
            log.error("  -> ECHEC : aucune donnée récupérée pour %s", series_id)
            failed.append(series_id)
            time.sleep(SLEEP_BETWEEN_CALLS)
            continue

        try:
            summary = write_ohlcv(df, asset_class="macro", symbol=series_id, timeframe=timeframe, source=SOURCE)
            n_rows = sum(summary.values())
            n_years = len(summary)
            log.info(
                "  -> OK : %d observations réparties sur %d fichier(s) annuel(s) (timeframe=%s, %s -> %s)",
                n_rows, n_years, timeframe, df["timestamp"].min().date(), df["timestamp"].max().date(),
            )
            ok.append(series_id)
        except Exception as e:
            log.error("  -> ECHEC écriture Parquet pour %s : %s", series_id, e)
            failed.append(series_id)

        time.sleep(SLEEP_BETWEEN_CALLS)

    elapsed = (datetime.now() - started_at).total_seconds()
    log.info("=" * 60)
    log.info("Terminé en %.1fs — %d OK, %d échecs", elapsed, len(ok), len(failed))
    if failed:
        log.info("Séries en échec : %s", ", ".join(failed))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
