"""
Sprint 3 — Ingestion fondamentaux US via SEC EDGAR (XBRL company concepts).

Usage :
    python packages/data-pipeline/ingest_secedgar.py
    python packages/data-pipeline/ingest_secedgar.py --limit 5
    python packages/data-pipeline/ingest_secedgar.py --symbols AAPL,MSFT

Fichier non listé dans l'arborescence initiale du brief (qui ne prévoyait
que ingest_alphavantage.py et ingest_fred.py pour ce sprint) — ajouté pour
couvrir "SEC EDGAR" explicitement assigné au Sprint 3 dans la feuille de
route, sur le même principe que les scripts test_connection_*.py ajoutés
librement au Sprint 0.

Portée : univers S&P 500 uniquement (universe.SP500). SEC EDGAR ne couvre
que les émetteurs déposant auprès du régulateur américain ; le CAC 40
(Euronext Paris) est hors périmètre de cette source (limitation documentée
dans docs/data-sources.md — la couverture Alpha Vantage sur ces valeurs
n'est pas fiable non plus en accès gratuit).

Pas de clé requise, mais la SEC exige un User-Agent identifiable
(nom du projet + contact) selon ses conditions d'usage — voir
SEC_EDGAR_USER_AGENT dans .env.example. Le brief indique "Aucune limite"
documentée pour cette source (pas de quota chiffré comme Alpha Vantage),
mais la politique de juste usage de la SEC recommande de rester sous les
~10 req/s ; ce script reste donc séquentiel avec une pause de courtoisie,
par prudence — contrairement à data.binance.vision (simple hébergement de
fichiers statiques), data.sec.gov surveille activement le débit par IP/UA
et peut bloquer un usage jugé abusif.

Récupère un jeu de métriques US-GAAP courantes (chiffre d'affaires, résultat
net, actifs/passifs, capitaux propres, BPA, actions en circulation) via
l'endpoint "company concept", avec repli sur des tags alternatifs quand le
tag principal n'est pas rapporté par une entreprise donnée (ex : bascule de
convention de nommage du chiffre d'affaires après l'adoption d'ASC 606).

Écrit dans la table SQLite `fundamentals` (ajoutée au schéma du brief, voir
fundamentals_db.py) plutôt que dans l'entrepôt Parquet, dimensionné pour des
séries OHLCV homogènes et peu adapté à des métriques hétérogènes rapportées
à fréquence irrégulière (trimestrielle/annuelle, selon les dépôts).
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
log = logging.getLogger("ingest_secedgar")

USER_AGENT = os.getenv("SEC_EDGAR_USER_AGENT", "").strip()
BASE_URL = "https://data.sec.gov"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
TICKER_MAP_CACHE = Path(os.getenv("DATA_RAW_DIR", "./data/raw")) / "sec_company_tickers.json"
TICKER_MAP_MAX_AGE_DAYS = 7

SOURCE = "sec_edgar"
SLEEP_BETWEEN_CALLS = 0.15  # ~7 req/s, sous le seuil de tolérance usuel de la SEC (10 req/s)
MAX_RETRIES = 3
TIMEOUT = 15

# métrique interne -> tags US-GAAP candidats, essayés dans l'ordre jusqu'au
# premier qui renvoie des données (toutes les entreprises ne rapportent pas
# les mêmes tags pour un même concept comptable).
CONCEPT_TAGS = {
    "revenue": ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"],
    "net_income": ["NetIncomeLoss"],
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "stockholders_equity": ["StockholdersEquity"],
    "eps_basic": ["EarningsPerShareBasic"],
    "eps_diluted": ["EarningsPerShareDiluted"],
    "shares_outstanding": ["CommonStockSharesOutstanding", "EntityCommonStockSharesOutstanding"],
}


def _headers() -> dict:
    return {"User-Agent": USER_AGENT, "Accept": "application/json"}


def _get_json(url: str) -> "dict | None":
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        except Exception as e:
            if attempt == MAX_RETRIES:
                log.warning("  échec réseau définitif pour %s : %s", url, e)
                return None
            time.sleep(1.5 * attempt)
            continue

        if resp.status_code == 404:
            return None  # concept non rapporté par cette entreprise, normal
        if resp.status_code != 200:
            if attempt == MAX_RETRIES:
                log.warning("  statut HTTP %d persistant pour %s", resp.status_code, url)
                return None
            time.sleep(1.5 * attempt)
            continue

        try:
            return resp.json()
        except ValueError:
            return None

    return None


def load_ticker_to_cik_map() -> dict:
    """Charge (avec cache local, TTL 7 jours) le mapping ticker -> CIK
    publié par la SEC. Le cache vit dans data/raw/ (gitignored), cohérent
    avec l'usage prévu de ce dossier pour l'état brut du pipeline."""
    if TICKER_MAP_CACHE.exists():
        age_days = (time.time() - TICKER_MAP_CACHE.stat().st_mtime) / 86400
        if age_days < TICKER_MAP_MAX_AGE_DAYS:
            return json.loads(TICKER_MAP_CACHE.read_text())

    payload = _get_json(TICKER_MAP_URL)
    if not payload:
        if TICKER_MAP_CACHE.exists():
            log.warning("  téléchargement du mapping ticker->CIK échoué, réutilisation du cache existant (périmé)")
            return json.loads(TICKER_MAP_CACHE.read_text())
        raise RuntimeError("Impossible de récupérer le mapping ticker->CIK depuis la SEC (pas de cache local)")

    mapping = {}
    for entry in payload.values():
        ticker = str(entry.get("ticker", "")).upper()
        cik = str(entry.get("cik_str", "")).zfill(10)
        if ticker:
            mapping[ticker] = cik

    TICKER_MAP_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TICKER_MAP_CACHE.write_text(json.dumps(mapping))
    return mapping


def resolve_cik(symbol: str, ticker_map: dict) -> "str | None":
    """Résout le CIK d'un ticker en tolérant les variantes de notation des
    classes d'actions (BRK-B/BRK.B, BF-B/BF.B...) — les tickers yfinance
    (convention du projet) et SEC EDGAR ne notent pas toujours ces cas
    identiquement."""
    candidates = [symbol.upper(), symbol.upper().replace("-", "."), symbol.upper().replace(".", "-")]
    for c in candidates:
        if c in ticker_map:
            return ticker_map[c]
    return None


def fetch_concept(cik: str, tag: str) -> "dict | None":
    url = f"{BASE_URL}/api/xbrl/companyconcept/CIK{cik}/us-gaap/{tag}.json"
    return _get_json(url)


def ingest_symbol(conn, symbol: str, name: str, cik: str) -> int:
    """Ingère les métriques disponibles pour un symbole. Retourne le nombre
    de points de données écrits (toutes périodes confondues)."""
    instrument_id = get_or_create_instrument(conn, symbol, asset_class="equity", name=name, exchange="US")
    n_written = 0

    for metric, tags in CONCEPT_TAGS.items():
        payload = None
        for tag in tags:
            payload = fetch_concept(cik, tag)
            time.sleep(SLEEP_BETWEEN_CALLS)
            if payload:
                break

        if not payload or "units" not in payload:
            continue

        for unit, facts in payload["units"].items():
            for fact in facts:
                val = fact.get("val")
                end = fact.get("end")
                if val is None or end is None:
                    continue
                fiscal_period = f"{fact.get('fp', '')}-{fact.get('fy', '')}".strip("-")
                upsert_fundamental(
                    conn, instrument_id, source=SOURCE, metric=metric, value=float(val),
                    as_of_date=fact.get("filed") or end, unit=unit, period_end=end,
                    fiscal_period=fiscal_period or None, form=fact.get("form"),
                )
                n_written += 1

    conn.commit()
    return n_written


def main():
    parser = argparse.ArgumentParser(description="Ingestion fondamentaux SEC EDGAR (S&P 500)")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de titres (tests)")
    parser.add_argument("--symbols", type=str, default=None, help="Liste CSV de tickers, ex: AAPL,MSFT")
    args = parser.parse_args()

    if not USER_AGENT:
        log.error(
            "SEC_EDGAR_USER_AGENT absente du .env — la SEC exige un User-Agent "
            "identifiable (nom du projet + email de contact). Voir .env.example."
        )
        sys.exit(1)

    universe = list(SP500)
    if args.symbols:
        wanted = {s.strip().upper() for s in args.symbols.split(",")}
        universe = [(s, n) for s, n in universe if s.upper() in wanted]
    if args.limit:
        universe = universe[: args.limit]

    log.info("Ingestion fondamentaux SEC EDGAR pour %d titres", len(universe))

    ticker_map = load_ticker_to_cik_map()
    conn = get_connection()

    ok, failed, unresolved = [], [], []
    started_at = datetime.now()

    try:
        for i, (symbol, name) in enumerate(universe, start=1):
            log.info("[%d/%d] %s", i, len(universe), symbol)
            cik = resolve_cik(symbol, ticker_map)
            if not cik:
                log.warning("  -> CIK introuvable pour %s (notation différente ou non coté SEC)", symbol)
                unresolved.append(symbol)
                continue

            try:
                n = ingest_symbol(conn, symbol, name, cik)
                if n == 0:
                    log.warning("  -> aucune métrique trouvée pour %s", symbol)
                    failed.append(symbol)
                else:
                    log.info("  -> OK : %d points de données fondamentales", n)
                    ok.append(symbol)
            except Exception as e:
                log.error("  -> ECHEC pour %s : %s", symbol, e)
                failed.append(symbol)
    finally:
        conn.close()

    elapsed = (datetime.now() - started_at).total_seconds()
    log.info("=" * 60)
    log.info(
        "Terminé en %.1fs — %d OK, %d échecs, %d CIK non résolus",
        elapsed, len(ok), len(failed), len(unresolved),
    )
    if unresolved:
        log.info("CIK non résolus : %s", ", ".join(unresolved))
    if failed:
        log.info("Échecs : %s", ", ".join(failed))

    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
