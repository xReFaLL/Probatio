"""
Sprint 5 — Connexion SQLite + fonctions d'accès aux métadonnées applicatives
(data/app.db, schéma défini dans packages/data-pipeline/init_db.py).

Mono-utilisateur pour le MVP : `user_id` toujours NULL (champ prévu par le
brief pour éviter un retrofit ultérieur si l'authentification est ajoutée
plus tard, pas encore utilisé).
"""
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("APP_DB_PATH", "./data/app.db")


def get_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def get_or_create_instrument(con: sqlite3.Connection, symbol: str, asset_class: str, name: str = None) -> int:
    row = con.execute(
        "SELECT id FROM instruments WHERE symbol = ? AND asset_class = ?",
        (symbol, asset_class),
    ).fetchone()
    if row:
        return row["id"]
    cur = con.execute(
        "INSERT INTO instruments (symbol, name, asset_class) VALUES (?, ?, ?)",
        (symbol, name or symbol, asset_class),
    )
    return cur.lastrowid


def create_strategy(con: sqlite3.Connection, name: str, description: str, rules_json: str) -> int:
    cur = con.execute(
        "INSERT INTO strategies (user_id, name, description, rules_json) VALUES (NULL, ?, ?, ?)",
        (name, description, rules_json),
    )
    return cur.lastrowid


def create_backtest_run(
    con: sqlite3.Connection, strategy_id: int, instrument_id: int, timeframe: str,
    start_date: str, end_date: str, initial_capital: float, commission: float,
    slippage: float, params_json: str,
) -> int:
    cur = con.execute(
        """
        INSERT INTO backtest_runs
            (user_id, strategy_id, instrument_id, timeframe, start_date, end_date,
             initial_capital, commission, slippage, params_json)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (strategy_id, instrument_id, timeframe, start_date, end_date,
         initial_capital, commission, slippage, params_json),
    )
    return cur.lastrowid


def insert_backtest_result(con: sqlite3.Connection, run_id: int, metrics: dict):
    con.execute(
        """
        INSERT INTO backtest_results
            (run_id, final_equity, sharpe, sortino, max_drawdown, win_rate, profit_factor, total_trades)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, metrics["final_equity"], metrics["sharpe"], metrics["sortino"],
            metrics["max_drawdown"], metrics["win_rate"], metrics["profit_factor"],
            metrics["total_trades"],
        ),
    )


def insert_trades(con: sqlite3.Connection, run_id: int, instrument_id: int, trades: list):
    if not trades:
        return
    con.executemany(
        """
        INSERT INTO trades
            (run_id, instrument_id, entry_time, entry_price, exit_time, exit_price, quantity, side, pnl)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (run_id, instrument_id, str(t["entry_time"]), t["entry_price"],
             str(t["exit_time"]), t["exit_price"], t["quantity"], t["side"], t["pnl"])
            for t in trades
        ],
    )


def insert_equity_curve(con: sqlite3.Connection, run_id: int, equity_curve):
    con.executemany(
        "INSERT INTO equity_curve_points (run_id, timestamp, equity) VALUES (?, ?, ?)",
        [
            (run_id, str(ts), float(eq))
            for ts, eq in zip(equity_curve["timestamp"], equity_curve["equity"])
        ],
    )