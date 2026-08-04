"""
Utilitaires SQLite partagés pour l'ingestion des données fondamentales
(SEC EDGAR, Alpha Vantage) — Sprint 3.

Choix d'architecture (point non couvert par le brief projet) : le schéma
SQLite du brief ne prévoit pas de table dédiée aux données fondamentales
(chiffre d'affaires, ratios de valorisation...). Deux options étaient
possibles : (a) les stocker dans l'entrepôt Parquet aux côtés des séries
OHLCV, ou (b) ajouter une table SQLite dédiée. Option (b) retenue par
défaut : les métriques fondamentales sont hétérogènes selon la source
(états financiers bruts pour SEC EDGAR, ratios de valorisation pour Alpha
Vantage) et rapportées à fréquence irrégulière (trimestrielle, ponctuelle),
ce qui correspond mal au schéma partitionné {symbol}/{timeframe}/{year} de
l'entrepôt marché, pensé pour des chandeliers OHLCV homogènes. Une table
SQLite en format long (une ligne par métrique) absorbe sans migration les
métriques disponibles selon la source.

`fundamentals` :
    instrument_id  -> FK vers instruments(id)
    source         -> 'sec_edgar' | 'alphavantage'
    metric         -> nom de la métrique (ex: 'revenue', 'PERatio')
    value          -> valeur numérique
    unit           -> unité si connue (ex: 'USD', 'USD/shares', 'shares')
    period_end     -> date de fin de période concernée (ex: fin d'exercice fiscal)
    fiscal_period  -> ex: 'FY-2024', 'Q3-2024'
    form           -> formulaire SEC d'origine si applicable (10-K, 10-Q)
    as_of_date     -> date de publication/observation de la donnée
    UNIQUE(instrument_id, source, metric, period_end) -> upsert idempotent,
    cohérent avec la stratégie "dernière valeur gagne" déjà utilisée dans
    parquet_writer.py aux Sprints 1-2.
"""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("APP_DB_PATH", "./data/app.db")

FUNDAMENTALS_SCHEMA = """
CREATE TABLE IF NOT EXISTS fundamentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    source TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL,
    unit TEXT,
    period_end TEXT,
    fiscal_period TEXT,
    form TEXT,
    as_of_date TEXT NOT NULL,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(instrument_id, source, metric, period_end)
);
"""


def get_connection() -> sqlite3.Connection:
    """Connexion SQLite vers data/app.db. Crée la table `fundamentals` si
    elle n'existe pas déjà (défensif, au cas où init_db.py n'aurait pas été
    relancé après cette mise à jour du schéma)."""
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(FUNDAMENTALS_SCHEMA)
    return conn


def get_or_create_instrument(
    conn: sqlite3.Connection,
    symbol: str,
    asset_class: str,
    name: "str | None" = None,
    exchange: "str | None" = None,
    currency: "str | None" = None,
) -> int:
    """Retourne l'id de l'instrument (symbol, asset_class), le crée si
    absent. Met à jour name/exchange/currency si une valeur non vide est
    fournie et que l'existant est vide (COALESCE) — utile car les scripts de
    fondamentaux (Alpha Vantage OVERVIEW notamment) renvoient souvent ces
    informations et peuvent enrichir un instrument déjà connu."""
    cur = conn.execute(
        "SELECT id FROM instruments WHERE symbol = ? AND asset_class = ?",
        (symbol, asset_class),
    )
    row = cur.fetchone()
    if row:
        instrument_id = row[0]
        conn.execute(
            "UPDATE instruments SET "
            "name = COALESCE(NULLIF(?, ''), name), "
            "exchange = COALESCE(NULLIF(?, ''), exchange), "
            "currency = COALESCE(NULLIF(?, ''), currency) "
            "WHERE id = ?",
            (name or "", exchange or "", currency or "", instrument_id),
        )
        return instrument_id

    cur = conn.execute(
        "INSERT INTO instruments (symbol, name, asset_class, exchange, currency) VALUES (?, ?, ?, ?, ?)",
        (symbol, name, asset_class, exchange, currency),
    )
    return cur.lastrowid


def upsert_fundamental(
    conn: sqlite3.Connection,
    instrument_id: int,
    source: str,
    metric: str,
    value: "float | None",
    as_of_date: str,
    unit: "str | None" = None,
    period_end: "str | None" = None,
    fiscal_period: "str | None" = None,
    form: "str | None" = None,
) -> None:
    """Insère ou met à jour (par instrument_id, source, metric, period_end)
    une métrique fondamentale. `period_end` ne doit pas être None si on veut
    un comportement d'upsert fiable : SQLite traite deux NULL comme
    distincts dans une contrainte UNIQUE, donc une valeur NULL empêcherait
    la détection de doublons entre exécutions successives -> les scripts
    appelants doivent toujours fournir une date de repli (ex: as_of_date)
    quand la source ne donne pas de période naturelle."""
    if value is None or period_end is None:
        return
    conn.execute(
        """
        INSERT INTO fundamentals
            (instrument_id, source, metric, value, unit, period_end, fiscal_period, form, as_of_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(instrument_id, source, metric, period_end) DO UPDATE SET
            value = excluded.value,
            unit = excluded.unit,
            fiscal_period = excluded.fiscal_period,
            form = excluded.form,
            as_of_date = excluded.as_of_date,
            ingested_at = datetime('now')
        """,
        (instrument_id, source, metric, value, unit, period_end, fiscal_period, form, as_of_date),
    )
