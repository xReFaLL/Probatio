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
    -- Sprint 7 -- 'rule_based' (sma_crossover, rsi_mean_reversion, ...,
    -- comportement historique -- valeur par défaut pour rester compatible
    -- avec les lignes créées avant ce sprint) ou 'custom_code' (stratégie
    -- utilisateur, code dans strategy_code, voir plus bas). `language` ne
    -- vaut pour l'instant que 'python' (voir brief -- justification du
    -- choix face à PineScript/MQL5), gardé en colonne plutôt qu'en valeur
    -- figée pour ne pas avoir à migrer le schéma si un jour un second
    -- langage sandboxé est ajouté.
    type TEXT NOT NULL DEFAULT 'rule_based' CHECK (type IN ('rule_based', 'custom_code')),
    language TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Sprint 7 -- code source des stratégies custom, versionné (une ligne par
-- version enregistrée, jamais écrasée -- permet de revenir sur une version
-- antérieure et de savoir avec quel code exact un backtest_run donné a été
-- produit, via rules_json.strategy_code_version_id sur le run correspondant).
CREATE TABLE IF NOT EXISTS strategy_code (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_id INTEGER NOT NULL REFERENCES strategies(id),
    code TEXT NOT NULL,
    -- 'vectorized' (generate_signals(df, params)) ou 'event_driven'
    -- (on_bar(context, bar)) -- voir packages/backtest-engine/sandbox/.
    mode TEXT NOT NULL DEFAULT 'vectorized' CHECK (mode IN ('vectorized', 'event_driven')),
    version INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(strategy_id, version)
);

-- Sprint 7 -- traçabilité de chaque exécution sandboxée (test rapide ou
-- backtest complet) : utile pour le débogage utilisateur (stdout/stderr
-- du sandbox) et pour un futur monitoring des temps d'exécution/timeouts.
CREATE TABLE IF NOT EXISTS strategy_execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- NULL si l'exécution n'a jamais donné lieu à un backtest_run persisté
    -- (ex. test rapide échoué, ou réussi mais jamais transformé en run complet).
    run_id INTEGER REFERENCES backtest_runs(id),
    strategy_code_id INTEGER NOT NULL REFERENCES strategy_code(id),
    -- 'quick_test' (échantillon réduit) ou 'full_run' (backtest complet).
    kind TEXT NOT NULL DEFAULT 'quick_test' CHECK (kind IN ('quick_test', 'full_run')),
    status TEXT NOT NULL CHECK (status IN ('ok', 'invalid', 'error', 'timeout')),
    stdout TEXT,
    stderr TEXT,
    execution_time_ms INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
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

-- Sprint 6 -- walk-forward analysis : une execution (config + grille de
-- parametres) donne plusieurs fenetres in-sample/out-of-sample.
CREATE TABLE IF NOT EXISTS walk_forward_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    strategy_name TEXT NOT NULL,
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    timeframe TEXT NOT NULL,
    param_grid_json TEXT NOT NULL,
    in_sample_bars INTEGER NOT NULL,
    out_sample_bars INTEGER NOT NULL,
    optimize_metric TEXT NOT NULL,
    engine TEXT NOT NULL DEFAULT 'vectorized',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS walk_forward_windows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    walk_forward_run_id INTEGER NOT NULL REFERENCES walk_forward_runs(id),
    window_index INTEGER NOT NULL,
    is_start TEXT NOT NULL,
    is_end TEXT NOT NULL,
    oos_start TEXT NOT NULL,
    oos_end TEXT NOT NULL,
    best_params_json TEXT NOT NULL,
    is_score REAL,
    oos_final_equity REAL,
    oos_sharpe REAL,
    oos_max_drawdown REAL,
    oos_total_trades INTEGER
);

-- Sprint 6 -- screener : une execution scanne un univers d'instruments avec
-- une meme strategie/parametres, un resultat par instrument retenu.
CREATE TABLE IF NOT EXISTS screener_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    strategy_name TEXT NOT NULL,
    params_json TEXT NOT NULL,
    asset_class TEXT,
    timeframe TEXT NOT NULL,
    rank_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS screener_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screener_run_id INTEGER NOT NULL REFERENCES screener_runs(id),
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    final_equity REAL,
    sharpe REAL,
    sortino REAL,
    max_drawdown REAL,
    win_rate REAL,
    profit_factor REAL,
    total_trades INTEGER
);

-- Sprint 6 -- portefeuille multi-actifs : une execution regroupe plusieurs
-- jambes (instrument + strategie + poids) et une courbe d'equity recombinee.
CREATE TABLE IF NOT EXISTS portfolio_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT,
    timeframe TEXT NOT NULL,
    initial_capital REAL NOT NULL,
    rebalance TEXT NOT NULL DEFAULT 'none',
    engine TEXT NOT NULL DEFAULT 'vectorized',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS portfolio_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_run_id INTEGER NOT NULL REFERENCES portfolio_runs(id),
    instrument_id INTEGER NOT NULL REFERENCES instruments(id),
    strategy_name TEXT NOT NULL,
    params_json TEXT NOT NULL,
    weight REAL NOT NULL,
    final_equity REAL,
    sharpe REAL
);

CREATE TABLE IF NOT EXISTS portfolio_equity_curve_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_run_id INTEGER NOT NULL REFERENCES portfolio_runs(id),
    timestamp TEXT NOT NULL,
    equity REAL NOT NULL
);
"""

# Sprint 6 -- `backtest_runs` existait deja avant l'introduction du moteur
# event-driven. Migration additive plutot que modification du schema
# ci-dessus : les bases deja initialisees avant ce sprint doivent continuer
# a s'ouvrir sans erreur (ALTER idempotent, on ignore si la colonne existe deja).
MIGRATIONS = [
    "ALTER TABLE backtest_runs ADD COLUMN engine TEXT NOT NULL DEFAULT 'vectorized'",
    # Sprint 7 -- bases initialisées avant l'introduction des stratégies
    # custom : `strategies` existe déjà sans les colonnes type/language.
    "ALTER TABLE strategies ADD COLUMN type TEXT NOT NULL DEFAULT 'rule_based'",
    "ALTER TABLE strategies ADD COLUMN language TEXT",
]


def main():
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_file)
    try:
        conn.executescript(SCHEMA)
        conn.executescript(FUNDAMENTALS_SCHEMA)  # table `fundamentals` — ajout Sprint 3, voir fundamentals_db.py
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
            except sqlite3.OperationalError:
                pass  # colonne deja presente (base initialisee a un sprint anterieur) -- idempotent
        conn.commit()
        print(f"[OK] Schéma SQLite initialisé dans {db_file.resolve()}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()