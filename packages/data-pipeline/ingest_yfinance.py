"""
Sprint 1 — Ingestion daily via yfinance pour l'univers de départ :
actions (S&P 500 + CAC 40), indices, forex, commodities.

Usage :
    python packages/data-pipeline/ingest_yfinance.py
    python packages/data-pipeline/ingest_yfinance.py --limit 10   # test rapide
    python packages/data-pipeline/ingest_yfinance.py --only equity
    python packages/data-pipeline/ingest_yfinance.py --symbols MMC,AAPL   # re-ingestion ciblée

Écrit dans data/warehouse/{asset_class}/{symbol}/1d/{year}.parquet via
parquet_writer.write_ohlcv. Ne fait AUCUN appel direct depuis le moteur de
backtest — ce script est le seul point d'entrée réseau pour yfinance.
"""
import argparse
import logging
import sys
import time
from datetime import datetime

import yfinance as yf

from universe import all_yfinance_symbols
from parquet_writer import write_ohlcv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_yfinance")

SOURCE = "yfinance"
TIMEFRAME = "1d"
# yfinance n'a pas de rate limit documenté officiellement, mais throttle en
# pratique au-delà d'un certain débit -> pause de courtoisie entre tickers.
SLEEP_BETWEEN_CALLS = 0.6
MAX_RETRIES = 3


def fetch_one(symbol: str) -> "pd.DataFrame | None":
    """Télécharge l'historique daily complet disponible pour un symbole."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            df = yf.download(
                symbol,
                period="max",
                interval="1d",
                progress=False,
                auto_adjust=False,
                multi_level_index=False,
            )
        except Exception as e:
            log.warning("  [%s] tentative %d/%d échouée : %s", symbol, attempt, MAX_RETRIES, e)
            time.sleep(2 * attempt)
            continue

        if df is None or df.empty:
            log.warning("  [%s] aucune donnée retournée (tentative %d/%d)", symbol, attempt, MAX_RETRIES)
            time.sleep(2 * attempt)
            continue

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        return df

    return None


def main():
    parser = argparse.ArgumentParser(description="Ingestion daily yfinance")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de symboles (tests)")
    parser.add_argument(
        "--only", choices=["equity", "index", "forex", "commodity"], default=None,
        help="Ne traiter qu'une classe d'actifs",
    )
    parser.add_argument(
        "--symbols", type=str, default=None,
        help="Liste de symboles séparés par des virgules, ex: MMC,AAPL (re-ingestion ciblée)",
    )
    args = parser.parse_args()

    symbols = all_yfinance_symbols()
    if args.only:
        symbols = [(s, ac) for s, ac in symbols if ac == args.only]
    if args.symbols:
        wanted = {s.strip().upper() for s in args.symbols.split(",")}
        symbols = [(s, ac) for s, ac in symbols if s.upper() in wanted]
        missing = wanted - {s.upper() for s, _ in symbols}
        if missing:
            log.warning("Symbole(s) inconnu(s) de l'univers (ignoré(s)) : %s", ", ".join(missing))
    if args.limit:
        symbols = symbols[: args.limit]

    log.info("Ingestion de %d symboles via yfinance (timeframe=%s)", len(symbols), TIMEFRAME)

    ok, failed = [], []
    started_at = datetime.now()

    for i, (symbol, asset_class) in enumerate(symbols, start=1):
        log.info("[%d/%d] %s (%s)", i, len(symbols), symbol, asset_class)
        df = fetch_one(symbol)

        if df is None:
            failed.append(symbol)
            time.sleep(SLEEP_BETWEEN_CALLS)
            continue

        try:
            summary = write_ohlcv(df, asset_class=asset_class, symbol=symbol, timeframe=TIMEFRAME, source=SOURCE)
            n_rows = sum(summary.values())
            n_years = len(summary)
            log.info("  -> OK : %d lignes réparties sur %d fichier(s) annuel(s)", n_rows, n_years)
            ok.append(symbol)
        except Exception as e:
            log.error("  -> ECHEC écriture Parquet pour %s : %s", symbol, e)
            failed.append(symbol)

        time.sleep(SLEEP_BETWEEN_CALLS)

    elapsed = (datetime.now() - started_at).total_seconds()
    log.info("=" * 60)
    log.info("Terminé en %.1fs — %d OK, %d échecs", elapsed, len(ok), len(failed))
    if failed:
        log.info("Symboles en échec : %s", ", ".join(failed))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()