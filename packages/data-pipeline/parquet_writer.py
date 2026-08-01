"""
Utilitaire d'écriture dans l'entrepôt Parquet marché.

Schéma de partition : data/warehouse/{asset_class}/{symbol}/{timeframe}/{year}.parquet
Colonnes : timestamp, open, high, low, close, volume, source, ingested_at

Écrit via DuckDB (déjà une dépendance du projet) plutôt que pyarrow, pour ne
pas ajouter de dépendance supplémentaire. Chaque écriture fusionne avec les
données existantes du fichier de l'année concernée et déduplique sur
`timestamp` (dernière valeur `ingested_at` gagne).
"""
import os
from pathlib import Path
from datetime import datetime, timezone

import duckdb
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

WAREHOUSE_DIR = Path(os.getenv("DATA_WAREHOUSE_DIR", "./data/warehouse"))

REQUIRED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def _sanitize_symbol(symbol: str) -> str:
    """Les tickers peuvent contenir des caractères non souhaitables dans un
    chemin de fichier (^, =, /) — on les remplace pour le nom de dossier."""
    return (
        symbol.replace("^", "IDX_")
        .replace("=", "_")
        .replace("/", "-")
    )


def write_ohlcv(
    df: pd.DataFrame,
    asset_class: str,
    symbol: str,
    timeframe: str,
    source: str,
) -> dict:
    """
    Écrit un DataFrame OHLCV dans l'entrepôt, partitionné par année.
    `df` doit contenir au minimum les colonnes REQUIRED_COLUMNS, avec un index
    ou une colonne `timestamp` de type datetime.

    Retourne un résumé {year: n_rows_written} pour logging.
    """
    if df is None or df.empty:
        return {}

    df = df.copy()

    if "timestamp" not in df.columns:
        df = df.reset_index()
        df = df.rename(columns={df.columns[0]: "timestamp"})

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Colonnes manquantes dans le DataFrame OHLCV : {missing}")

    df = df[REQUIRED_COLUMNS].dropna(subset=["timestamp"])
    df["source"] = source
    df["ingested_at"] = datetime.now(timezone.utc)

    safe_symbol = _sanitize_symbol(symbol)
    base_dir = WAREHOUSE_DIR / asset_class / safe_symbol / timeframe
    base_dir.mkdir(parents=True, exist_ok=True)

    df["_year"] = df["timestamp"].dt.year
    summary = {}

    con = duckdb.connect()
    try:
        for year, group in df.groupby("_year"):
            group = group.drop(columns=["_year"])
            out_path = base_dir / f"{year}.parquet"

            con.register("new_data", group)
            # DuckDB ne permet pas d'écrire dans un fichier en cours de lecture
            # dans la même requête : on écrit systématiquement vers un fichier
            # temporaire puis on le déplace en remplacement de l'original.
            tmp_path = out_path.with_suffix(".tmp.parquet")
            if out_path.exists():
                # Fusion + déduplication : on garde, pour chaque timestamp,
                # la ligne avec le ingested_at le plus récent.
                query = f"""
                    COPY (
                        SELECT * EXCLUDE (rn) FROM (
                            SELECT *, ROW_NUMBER() OVER (
                                PARTITION BY timestamp ORDER BY ingested_at DESC
                            ) AS rn
                            FROM (
                                SELECT * FROM read_parquet('{out_path.as_posix()}')
                                UNION ALL
                                SELECT * FROM new_data
                            )
                        ) WHERE rn = 1
                        ORDER BY timestamp
                    ) TO '{tmp_path.as_posix()}' (FORMAT PARQUET)
                """
            else:
                query = f"""
                    COPY (SELECT * FROM new_data ORDER BY timestamp)
                    TO '{tmp_path.as_posix()}' (FORMAT PARQUET)
                """
            con.execute(query)
            tmp_path.replace(out_path)
            con.unregister("new_data")

            summary[int(year)] = len(group)
    finally:
        con.close()

    return summary
