"""
Initialise le fichier SQLite des métadonnées applicatives (data/app.db) avec
le schéma défini dans le brief projet. Mono-utilisateur pour le MVP : pas de
table `users`, mais un champ `user_id` nullable est prévu dans `strategies`
et `backtest_runs` pour éviter un retrofit ultérieur.

Sprint 3 : ajoute également la table `fundamentals` (non prévue dans le
schéma initial du brief — voir fundamentals_db.py pour la justification de
ce choix par défaut).

Usage : python packages/data-pipeline/init_db.py
"""
import os
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

from fundamentals_db import FUNDAMENTALS_SCHEMA

load_dotenv()

DB_PATH = os.getenv("APP_DB_PATH", "./data/app.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    name TEXT,
    asset_class TEXT NOT NULL,
    exchange TEXT,
    currency TEXT,
    UNIQUE(symbol, asset_class)
);

CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT NOT NULL,
    description TEXT,
    rules_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timeframe TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    commission REAL NOT NULL DEFAULT 0,
    slippage REAL NOT NULL DEFAULT 0,
    params_json TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id),
    final_equity REAL,
    sharpe REAL,
    sortino REAL,
    max_drawdown REAL,
    win_rate REAL,
    profit_factor REAL,
    total_trades INTEGER
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id),
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    entry_time TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_time TEXT,
    exit_price REAL,
    quantity REAL NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('long', 'short')),
    pnl REAL
);

CREATE TABLE IF NOT EXISTS equity_curve_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id),
    timestamp TEXT NOT NULL,
    equity REAL NOT NULL
);
"""


def main():
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(SCHEMA)
        conn.executescript(FUNDAMENTALS_SCHEMA)  # table `fundamentals` — ajout Sprint 3, voir fundamentals_db.py
        conn.commit()
        print(f"[OK] Schéma SQLite initialisé dans {db_file.resolve()}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
