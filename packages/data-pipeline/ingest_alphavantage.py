"""
Sprint 3 — Ingestion fondamentaux "backup" via Alpha Vantage (endpoint
OVERVIEW), en complément de SEC EDGAR : ratios de valorisation dérivés du
cours (PE, PEG, Beta, marges...) qu'un filing SEC brut ne calcule pas.

Usage :
    python packages/data-pipeline/ingest_alphavantage.py                # traite le prochain lot (curseur)
    python packages/data-pipeline/ingest_alphavantage.py --batch-size 5
    python packages/data-pipeline/ingest_alphavantage.py --symbols AAPL,MSFT  # symboles précis, ne touche pas au curseur

Contrainte structurante : 25 requêtes/jour, 5/min (brief projet). Avec 503
titres S&P 500 à couvrir, une ingestion complète en une exécution est
impossible. Ce script traite donc un lot borné (20 par défaut, marge sous la
limite quotidienne) et persiste sa progression dans un curseur JSON
(data/raw/) pour pouvoir être relancé quotidiennement — via cron ou, plus
tard, APScheduler (scheduler.py reste un placeholder, son implémentation
n'est pas assignée à ce sprint) — et couvrir tout l'univers en cycle roulant
(~26 jours à 20 titres/jour), puis recommencer : les fondamentaux étant
publiés trimestriellement, un cycle de renouvellement de quelques semaines
reste pertinent plutôt qu'un one-shot.

CAC 40 hors périmètre, comme pour SEC EDGAR : la couverture fondamentaux
d'Alpha Vantage sur les valeurs Euronext Paris est peu fiable en accès
gratuit (limitation documentée dans docs/data-sources.md).
"""
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

from universe import SP500
from fundamentals_db import get_connection, get_or_create_instrument, upsert_fundamental

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_alphavantage")

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"
SOURCE = "alphavantage"
DEFAULT_BATCH_SIZE = 20      # marge de sécurité sous la limite de 25 requêtes/jour
SLEEP_BETWEEN_CALLS = 15     # limite 5/min -> 12s minimum ; marge de sécurité à 15s
MAX_RETRIES = 2
TIMEOUT = 15
CURSOR_PATH = Path(os.getenv("DATA_RAW_DIR", "./data/raw")) / "alphavantage_fundamentals_cursor.json"

# Champs numériques de la réponse OVERVIEW conservés comme métriques
# fondamentales. Les champs texte (Name, Sector, Exchange, Currency...) ne
# sont pas stockés dans `fundamentals` (colonne value=REAL) mais utilisés
# pour enrichir directement la table `instruments` via get_or_create_instrument.
NUMERIC_FIELDS = [
    "MarketCapitalization", "EBITDA", "PERatio", "PEGRatio", "BookValue",
    "DividendPerShare", "DividendYield", "EPS", "RevenuePerShareTTM",
    "ProfitMargin", "OperatingMarginTTM", "ReturnOnAssetsTTM", "ReturnOnEquityTTM",
    "RevenueTTM", "GrossProfitTTM", "DilutedEPSTTM", "QuarterlyEarningsGrowthYOY",
    "QuarterlyRevenueGrowthYOY", "AnalystTargetPrice", "TrailingPE", "ForwardPE",
    "PriceToSalesRatioTTM", "PriceToBookRatio", "EVToRevenue", "EVToEBITDA",
    "Beta", "52WeekHigh", "52WeekLow", "50DayMovingAverage", "200DayMovingAverage",
    "SharesOutstanding",
]


def _load_cursor() -> int:
    if CURSOR_PATH.exists():
        try:
            return int(json.loads(CURSOR_PATH.read_text()).get("next_index", 0))
        except (ValueError, OSError, TypeError):
            return 0
    return 0


def _save_cursor(next_index: int) -> None:
    CURSOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    CURSOR_PATH.write_text(json.dumps({"next_index": next_index, "updated_at": datetime.now().isoformat()}))


def fetch_overview(symbol: str) -> "tuple[dict | None, bool]":
    """Retourne (payload, quota_exceeded). payload est None si aucune donnée
    exploitable ; quota_exceeded distingue un vrai dépassement de quota
    (message 'Note'/'Information' d'Alpha Vantage) d'un échec ponctuel, pour
    savoir s'il faut interrompre le lot en cours."""
    params = {"function": "OVERVIEW", "symbol": symbol, "apikey": API_KEY}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
            payload = resp.json()
        except Exception as e:
            log.warning("  tentative %d/%d échouée pour %s : %s", attempt, MAX_RETRIES, symbol, e)
            time.sleep(3)
            continue

        if "Note" in payload or "Information" in payload:
            log.error(
                "  message Alpha Vantage (probable quota atteint) : %s",
                payload.get("Note") or payload.get("Information"),
            )
            return None, True

        if not payload or "Symbol" not in payload:
            log.warning("  réponse vide/inattendue pour %s : %s", symbol, payload)
            return None, False

        return payload, False

    return None, False


def ingest_overview(conn, symbol: str, fallback_name: str, payload: dict) -> int:
    instrument_id = get_or_create_instrument(
        conn, symbol, asset_class="equity",
        name=payload.get("Name") or fallback_name,
        exchange=payload.get("Exchange"),
        currency=payload.get("Currency"),
    )

    # LatestQuarter donne la période fiscale la plus récente couverte par le
    # snapshot -> sert de period_end pour un upsert idempotent (voir
    # fundamentals_db.upsert_fundamental) ; repli sur la date du jour si
    # absente (rare, mais évite un period_end=None qui casserait l'upsert).
    period_end = payload.get("LatestQuarter") or datetime.now().date().isoformat()

    n_written = 0
    for field in NUMERIC_FIELDS:
        raw = payload.get(field)
        if raw in (None, "None", "-", ""):
            continue
        try:
            value = float(raw)
        except ValueError:
            continue
        upsert_fundamental(
            conn, instrument_id, source=SOURCE, metric=field, value=value,
            as_of_date=datetime.now().date().isoformat(), period_end=period_end,
            fiscal_period=payload.get("FiscalYearEnd"),
        )
        n_written += 1

    conn.commit()
    return n_written


def main():
    parser = argparse.ArgumentParser(description="Ingestion fondamentaux Alpha Vantage (OVERVIEW, cycle roulant)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--symbols", type=str, default=None, help="Traiter des symboles précis (n'avance pas le curseur)")
    args = parser.parse_args()

    if not API_KEY:
        log.error("ALPHAVANTAGE_API_KEY absente du .env — voir .env.example")
        sys.exit(1)

    universe = list(SP500)

    if args.symbols:
        wanted = {s.strip().upper() for s in args.symbols.split(",")}
        batch = [(s, n) for s, n in universe if s.upper() in wanted]
        advance_cursor = False
    else:
        start = _load_cursor() % len(universe)
        batch = [universe[(start + i) % len(universe)] for i in range(args.batch_size)]
        advance_cursor = True

    log.info(
        "Ingestion Alpha Vantage OVERVIEW pour %d titre(s) (limite 25/jour, 5/min -> pause %ds entre appels)",
        len(batch), SLEEP_BETWEEN_CALLS,
    )

    conn = get_connection()
    ok, failed = [], []
    processed = 0
    started_at = datetime.now()

    try:
        for i, (symbol, name) in enumerate(batch, start=1):
            log.info("[%d/%d] %s", i, len(batch), symbol)
            payload, quota_hit = fetch_overview(symbol)

            if payload is None:
                failed.append(symbol)
                if quota_hit:
                    log.error("  arrêt anticipé du lot (quota Alpha Vantage probablement atteint)")
                    break
                processed = i
                if i < len(batch):
                    time.sleep(SLEEP_BETWEEN_CALLS)
                continue

            n = ingest_overview(conn, symbol, name, payload)
            log.info("  -> OK : %d métriques", n)
            ok.append(symbol)
            processed = i

            if i < len(batch):
                time.sleep(SLEEP_BETWEEN_CALLS)
    finally:
        conn.close()

    if advance_cursor and processed:
        new_index = (_load_cursor() + processed) % len(universe)
        _save_cursor(new_index)
        log.info("Curseur avancé de %d position(s) (prochain index : %d/%d)", processed, new_index, len(universe))

    elapsed = (datetime.now() - started_at).total_seconds()
    log.info("=" * 60)
    log.info("Terminé en %.1fs — %d OK, %d échecs", elapsed, len(ok), len(failed))
    if failed:
        log.info("Échecs : %s", ", ".join(failed))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
