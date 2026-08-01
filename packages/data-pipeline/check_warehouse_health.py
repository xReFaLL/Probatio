"""
Bilan de santé de l'entrepôt — à lancer avant de passer au Sprint 4.

Les tests de connexion (test_all_connections.py) vérifient seulement que les
APIs répondent. Ce script vérifie que les données ingérées aux Sprints 1-3
sont réellement présentes dans data/warehouse et data/app.db, et repère les
symboles manquants ou les trous évidents — pour ne pas déboguer le moteur de
backtest du Sprint 4 sur des fondations silencieusement incomplètes.

Usage :
    python packages/data-pipeline/check_warehouse_health.py

Lecture des résultats :
  - "X/Y symboles présents" : combien de l'univers attendu ont au moins un
    fichier dans l'entrepôt. En dessous de 100%, c'est normal si tu n'as pas
    encore relancé une ingestion complète (ex: yfinance throttle, ou script
    lancé avec --limit pour un test rapide) — mais à vérifier si le nombre
    manquant est important.
  - Plage de dates : à comparer à ce que tu attends (le brief vise 20-30 ans
    pour les actions/indices/forex/commodities, depuis 2017 pour la crypto).
    Une plage très courte (quelques mois) sur une classe d'actifs entière
    signale probablement un souci d'ingestion, pas juste un symbole isolé.
  - "valeur OHLC manquante" : ne devrait jamais arriver au vu du pipeline
    actuel (dropna à l'écriture) — si >0, à investiguer avant le Sprint 4.
"""
import os
import sqlite3
from pathlib import Path

import duckdb
from dotenv import load_dotenv

from universe import (
    SP500, CAC40, INDICES, FOREX_PAIRS, COMMODITIES, CRYPTO_PAIRS, MACRO_SERIES,
)
from parquet_writer import _sanitize_symbol

load_dotenv()

WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))
DB_PATH = Path(os.getenv("APP_DB_PATH", "./data/app.db"))

EXPECTED = {
    "equity": [s for s, _ in SP500] + [s for s, _ in CAC40],
    "index": [s for s, _ in INDICES],
    "forex": [s for s, _ in FOREX_PAIRS],
    "commodity": [s for s, _ in COMMODITIES],
    "crypto": list(CRYPTO_PAIRS),
    "macro": [s for s, _ in MACRO_SERIES],
}


def check_sqlite():
    print("=== SQLite (data/app.db) ===")
    if not DB_PATH.exists():
        print("  [MANQUANT] data/app.db n'existe pas encore — lancer init_db.py")
        return

    con = sqlite3.connect(str(DB_PATH))
    try:
        for table in ["instruments", "strategies", "backtest_runs", "fundamentals"]:
            try:
                n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"  {table:<16} {n:>6} ligne(s)")
            except sqlite3.OperationalError:
                print(f"  {table:<16} [MANQUANT] table absente — relancer init_db.py")
    finally:
        con.close()


def check_asset_class(asset_class: str, expected_symbols: list):
    print(f"\n=== {asset_class} ===")
    base = WAREHOUSE_DIR / asset_class
    if not base.exists():
        print(f"  [MANQUANT] Aucun dossier {asset_class}/ dans l'entrepôt — "
              f"le script d'ingestion correspondant n'a peut-être pas encore tourné.")
        return

    present = {p.name for p in base.iterdir() if p.is_dir()}
    expected_safe = {_sanitize_symbol(s): s for s in expected_symbols}
    missing = [orig for safe, orig in expected_safe.items() if safe not in present]
    n_present = len(expected_safe) - len(missing)

    print(f"  {n_present}/{len(expected_safe)} symboles présents dans l'entrepôt")
    if missing:
        preview = ", ".join(missing[:10])
        more = f" (+{len(missing) - 10} autres)" if len(missing) > 10 else ""
        print(f"  Manquants : {preview}{more}")

    glob_pattern = (base / "*" / "*" / "*.parquet").as_posix()
    con = duckdb.connect()
    try:
        row = con.execute(f"""
            SELECT
                COUNT(*),
                MIN(timestamp),
                MAX(timestamp),
                SUM(CASE WHEN open IS NULL OR high IS NULL OR low IS NULL
                         OR close IS NULL THEN 1 ELSE 0 END)
            FROM read_parquet('{glob_pattern}', union_by_name=True)
        """).fetchone()
    except duckdb.IOException:
        row = None
    finally:
        con.close()

    if row is None or row[0] == 0:
        print("  Aucune ligne de données trouvée dans les fichiers présents.")
        return

    n_rows, min_ts, max_ts, n_nulls = row
    print(f"  {n_rows:,} lignes au total, du {str(min_ts)[:10]} au {str(max_ts)[:10]}")
    if n_nulls:
        print(f"  [ATTENTION] {n_nulls} ligne(s) avec une valeur OHLC manquante :")
        con = duckdb.connect()
        try:
            detail_rows = con.execute(f"""
                SELECT filename, timestamp
                FROM read_parquet('{glob_pattern}', union_by_name=True, filename=True)
                WHERE open IS NULL OR high IS NULL OR low IS NULL OR close IS NULL
                ORDER BY filename, timestamp
                LIMIT 30
            """).fetchall()
        finally:
            con.close()
        for filename, ts in detail_rows:
            # data/warehouse/{asset_class}/{symbol}/{timeframe}/{year}.parquet
            symbol = Path(filename).parent.parent.name
            print(f"    {symbol:<8} {str(ts)[:10]}")
        if n_nulls > len(detail_rows):
            print(f"    ... et {n_nulls - len(detail_rows)} autre(s)")


def main():
    check_sqlite()
    for asset_class, symbols in EXPECTED.items():
        check_asset_class(asset_class, symbols)

    print(
        "\n=== Fait ===\n"
        "Regarde surtout : des classes d'actifs entièrement vides (dossier "
        "manquant), des plages de dates anormalement courtes, ou des valeurs "
        "OHLC manquantes. Un symbole isolé manquant (ticker radié, paire pas "
        "encore cotée en 2017...) est normal et documenté dans "
        "docs/data-sources.md (biais de survivance)."
    )


if __name__ == "__main__":
    main()