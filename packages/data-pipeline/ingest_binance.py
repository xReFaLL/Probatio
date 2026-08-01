"""
Sprint 2 — Ingestion historique crypto via Binance public data
(data.binance.vision), pour l'univers de paires USDT retenu (voir
universe.CRYPTO_PAIRS).

Usage :
    python packages/data-pipeline/ingest_binance.py
    python packages/data-pipeline/ingest_binance.py --limit 3              # test rapide
    python packages/data-pipeline/ingest_binance.py --symbols BTCUSDT,ETHUSDT
    python packages/data-pipeline/ingest_binance.py --interval 1h          # autre granularité

Stratégie de téléchargement :
  1. Archives MENSUELLES (data/spot/monthly/klines/{symbol}/{interval}/...)
     pour tout l'historique depuis le lancement de Binance (2017-08) jusqu'au
     dernier mois calendaire complet -> ~1 fichier par mois-symbole au lieu
     d'un par jour, nettement plus efficace pour "toute l'histoire depuis
     2017".
  2. Archives QUOTIDIENNES pour compléter le mois en cours, dont l'archive
     mensuelle n'est pas encore publiée.

Un 404 sur un mois antérieur à la cotation d'une paire est normal (la paire
n'existait pas encore sur Binance) et n'est pas compté comme un échec — seuls
les symboles pour lesquels AUCUNE donnée n'a pu être récupérée sont reportés
en échec.

data.binance.vision est un simple serveur de fichiers statiques (bucket S3),
pas une API avec limite de débit documentée (voir brief projet et
test_connection_binance.py du Sprint 0) — on parallélise donc les
téléchargements d'un même symbole, ce qui reste courtois pour ce type
d'hébergement. Conformément au principe "aucune API en direct depuis le
moteur de backtest", ce script est le seul point d'entrée réseau vers
Binance ; il écrit dans l'entrepôt Parquet via parquet_writer.write_ohlcv,
qui déduplique sur `timestamp` (ré-exécutions sûres, idempotentes).
"""
import argparse
import io
import logging
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta

import pandas as pd
import requests

from universe import CRYPTO_PAIRS
from parquet_writer import write_ohlcv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("ingest_binance")

SOURCE = "binance"
BASE_URL = "https://data.binance.vision/data/spot"
LAUNCH_YEAR_MONTH = (2017, 8)  # premiers historiques disponibles sur data.binance.vision
MAX_WORKERS = 10
MAX_RETRIES = 3
TIMEOUT = 20

# Colonnes des fichiers klines Binance (archives sans en-tête, format historique) :
# https://github.com/binance/binance-public-data/blob/master/data-guide.md
KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "count",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


def _months_from_launch_to_last_complete():
    """Liste des (année, mois) depuis le lancement jusqu'au dernier mois
    calendaire complet (le mois en cours n'a pas encore d'archive mensuelle)."""
    today = date.today()
    if today.month == 1:
        last_complete = (today.year - 1, 12)
    else:
        last_complete = (today.year, today.month - 1)

    months = []
    year, month = LAUNCH_YEAR_MONTH
    while (year, month) <= last_complete:
        months.append((year, month))
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _days_of_current_month_until_yesterday():
    """Jours du mois en cours jusqu'à hier inclus (aujourd'hui n'est pas
    encore clôturé, son archive quotidienne n'existe pas)."""
    today = date.today()
    d = today.replace(day=1)
    days = []
    while d < today:
        days.append(d)
        d += timedelta(days=1)
    return days


def _download_zip(url: str) -> "bytes | None":
    """Télécharge une archive. Renvoie None si absente (404 normal) ou après
    échec des tentatives sur erreur réseau/HTTP transitoire."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, timeout=TIMEOUT)
        except Exception as e:
            if attempt == MAX_RETRIES:
                log.warning("  échec réseau définitif pour %s : %s", url, e)
                return None
            time.sleep(1.5 * attempt)
            continue

        if resp.status_code == 404:
            return None  # pas encore coté à cette date / archive pas encore publiée
        if resp.status_code != 200:
            if attempt == MAX_RETRIES:
                log.warning("  statut HTTP %d persistant pour %s", resp.status_code, url)
                return None
            time.sleep(1.5 * attempt)
            continue

        return resp.content

    return None


def _parse_klines_zip(content: bytes) -> "pd.DataFrame | None":
    """Extrait et parse le CSV contenu dans une archive klines Binance.

    Gère deux variations de format rencontrées dans les archives publiques :
      - anciennes archives : pas d'en-tête, colonnes dans l'ordre KLINE_COLUMNS
      - archives plus récentes : première ligne = en-tête explicite
      - `open_time` en millisecondes (historique) ou en microsecondes
        (bascule opérée par Binance sur une partie des archives récentes) :
        normalisé par ordre de grandeur.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            names = zf.namelist()
            if not names:
                return None
            with zf.open(names[0]) as f:
                raw = f.read()
    except zipfile.BadZipFile as e:
        log.warning("  archive zip invalide : %s", e)
        return None

    if not raw:
        return None

    first_line = raw.split(b"\n", 1)[0].decode("utf-8", errors="ignore").strip()
    first_token = first_line.split(",")[0].strip()
    has_header = not first_token.lstrip("-").isdigit()

    buf = io.BytesIO(raw)
    if has_header:
        df = pd.read_csv(buf)
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    else:
        df = pd.read_csv(buf, header=None, names=KLINE_COLUMNS)

    if df.empty or "open_time" not in df.columns:
        return None

    df["open_time"] = pd.to_numeric(df["open_time"], errors="coerce")
    df = df.dropna(subset=["open_time"])
    if df.empty:
        return None

    # ms vs µs : un epoch en microsecondes dépasse 10^14 pour toute date
    # postérieure à 2001, alors qu'un epoch en millisecondes ne l'atteint
    # qu'en l'an 5138 -> seuil sûr pour distinguer les deux.
    if df["open_time"].iloc[0] > 10**14:
        df["open_time"] = df["open_time"] // 1000

    df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df = df.dropna(subset=["open", "high", "low", "close"])
    return df if not df.empty else None


def fetch_symbol_history(symbol: str, interval: str) -> pd.DataFrame:
    """Récupère l'historique complet disponible pour une paire, en combinant
    archives mensuelles (gros du volume) et quotidiennes (mois en cours)."""
    monthly_urls = [
        f"{BASE_URL}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{y:04d}-{m:02d}.zip"
        for y, m in _months_from_launch_to_last_complete()
    ]
    daily_urls = [
        f"{BASE_URL}/daily/klines/{symbol}/{interval}/{symbol}-{interval}-{d.isoformat()}.zip"
        for d in _days_of_current_month_until_yesterday()
    ]
    all_urls = monthly_urls + daily_urls

    frames = []
    missing = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(_download_zip, url): url for url in all_urls}
        for future in as_completed(futures):
            content = future.result()
            if content is None:
                missing += 1
                continue
            df = _parse_klines_zip(content)
            if df is not None:
                frames.append(df)

    log.info(
        "  %d/%d archives récupérées (%d absentes — normal avant cotation ou mois non encore publié)",
        len(all_urls) - missing, len(all_urls), missing,
    )

    if not frames:
        return pd.DataFrame()

    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset="timestamp").sort_values("timestamp").reset_index(drop=True)
    return out


def main():
    parser = argparse.ArgumentParser(description="Ingestion historique Binance (klines)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de paires (tests)")
    parser.add_argument("--symbols", type=str, default=None, help="Liste CSV de paires, ex: BTCUSDT,ETHUSDT")
    parser.add_argument("--interval", type=str, default="1d", help="Granularité Binance (défaut : 1d)")
    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else list(CRYPTO_PAIRS)
    if args.limit:
        symbols = symbols[: args.limit]

    log.info("Ingestion de %d paires via Binance public data (interval=%s)", len(symbols), args.interval)

    ok, failed = [], []
    started_at = datetime.now()

    for i, symbol in enumerate(symbols, start=1):
        log.info("[%d/%d] %s", i, len(symbols), symbol)
        df = fetch_symbol_history(symbol, args.interval)

        if df.empty:
            log.error("  -> ECHEC : aucune donnée récupérée pour %s", symbol)
            failed.append(symbol)
            continue

        try:
            summary = write_ohlcv(
                df, asset_class="crypto", symbol=symbol, timeframe=args.interval, source=SOURCE
            )
            n_rows = sum(summary.values())
            n_years = len(summary)
            log.info(
                "  -> OK : %d lignes réparties sur %d fichier(s) annuel(s) (%s -> %s)",
                n_rows, n_years, df["timestamp"].min().date(), df["timestamp"].max().date(),
            )
            ok.append(symbol)
        except Exception as e:
            log.error("  -> ECHEC écriture Parquet pour %s : %s", symbol, e)
            failed.append(symbol)

    elapsed = (datetime.now() - started_at).total_seconds()
    log.info("=" * 60)
    log.info("Terminé en %.1fs — %d OK, %d échecs", elapsed, len(ok), len(failed))
    if failed:
        log.info("Paires en échec : %s", ", ".join(failed))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
