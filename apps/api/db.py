"""
Sprint 5 — Connexion SQLite + fonctions d'accès aux métadonnées applicatives
(data/app.db, schéma défini dans packages/data-pipeline/init_db.py).

Mono-utilisateur pour le MVP : `user_id` toujours NULL (champ prévu par le
brief pour éviter un retrofit ultérieur si l'authentification est ajoutée
plus tard, pas encore utilisé).

Sprint 6 : ajoute la persistance du walk-forward, du screener et des
portefeuilles multi-actifs (voir sections dédiées ci-dessous).
"""
import json
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


def create_strategy(
    con: sqlite3.Connection, name: str, description: str, rules_json: str,
    type_: str = "rule_based", language: str = None,
) -> int:
    cur = con.execute(
        "INSERT INTO strategies (user_id, name, description, rules_json, type, language) "
        "VALUES (NULL, ?, ?, ?, ?, ?)",
        (name, description, rules_json, type_, language),
    )
    return cur.lastrowid


def create_backtest_run(
    con: sqlite3.Connection, strategy_id: int, instrument_id: int, timeframe: str,
    start_date: str, end_date: str, initial_capital: float, commission: float,
    slippage: float, params_json: str, engine: str = "vectorized",
) -> int:
    cur = con.execute(
        """
        INSERT INTO backtest_runs
            (user_id, strategy_id, instrument_id, timeframe, start_date, end_date,
             initial_capital, commission, slippage, params_json, engine)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (strategy_id, instrument_id, timeframe, start_date, end_date,
         initial_capital, commission, slippage, params_json, engine),
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


# --- Sprint 6 -- walk-forward analysis --------------------------------------

def create_walk_forward_run(
    con: sqlite3.Connection, strategy_name: str, instrument_id: int, timeframe: str,
    param_grid_json: str, in_sample_bars: int, out_sample_bars: int,
    optimize_metric: str, engine: str,
) -> int:
    cur = con.execute(
        """
        INSERT INTO walk_forward_runs
            (user_id, strategy_name, instrument_id, timeframe, param_grid_json,
             in_sample_bars, out_sample_bars, optimize_metric, engine)
        VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (strategy_name, instrument_id, timeframe, param_grid_json,
         in_sample_bars, out_sample_bars, optimize_metric, engine),
    )
    return cur.lastrowid


def insert_walk_forward_windows(con: sqlite3.Connection, walk_forward_run_id: int, windows: list):
    con.executemany(
        """
        INSERT INTO walk_forward_windows
            (walk_forward_run_id, window_index, is_start, is_end, oos_start, oos_end,
             best_params_json, is_score, oos_final_equity, oos_sharpe, oos_max_drawdown, oos_total_trades)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                walk_forward_run_id, w["window_index"], w["is_start"], w["is_end"],
                w["oos_start"], w["oos_end"], json.dumps(w["best_params"]), w["is_score"],
                w["oos_metrics"].get("final_equity"), w["oos_metrics"].get("sharpe"),
                w["oos_metrics"].get("max_drawdown"), w["oos_metrics"].get("total_trades"),
            )
            for w in windows
        ],
    )


def list_walk_forward_runs(con: sqlite3.Connection, limit: int = 50) -> list:
    rows = con.execute(
        """
        SELECT wfr.id AS walk_forward_run_id, i.symbol, wfr.strategy_name AS strategy,
               wfr.created_at, COUNT(wfw.id) AS n_windows,
               AVG(wfw.oos_sharpe) AS aggregate_sharpe
        FROM walk_forward_runs wfr
        JOIN instruments i ON i.id = wfr.instrument_id
        LEFT JOIN walk_forward_windows wfw ON wfw.walk_forward_run_id = wfr.id
        GROUP BY wfr.id
        ORDER BY wfr.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_walk_forward_run(con: sqlite3.Connection, walk_forward_run_id: int):
    run = con.execute(
        """
        SELECT wfr.*, i.symbol, i.asset_class
        FROM walk_forward_runs wfr
        JOIN instruments i ON i.id = wfr.instrument_id
        WHERE wfr.id = ?
        """,
        (walk_forward_run_id,),
    ).fetchone()
    if run is None:
        return None, []
    windows = con.execute(
        "SELECT * FROM walk_forward_windows WHERE walk_forward_run_id = ? ORDER BY window_index",
        (walk_forward_run_id,),
    ).fetchall()
    return dict(run), [dict(w) for w in windows]


# --- Sprint 6 -- screener ----------------------------------------------------

def create_screener_run(
    con: sqlite3.Connection, strategy_name: str, params_json: str, asset_class: str,
    timeframe: str, rank_by: str,
) -> int:
    cur = con.execute(
        """
        INSERT INTO screener_runs (user_id, strategy_name, params_json, asset_class, timeframe, rank_by)
        VALUES (NULL, ?, ?, ?, ?, ?)
        """,
        (strategy_name, params_json, asset_class, timeframe, rank_by),
    )
    return cur.lastrowid


def insert_screener_results(con: sqlite3.Connection, screener_run_id: int, instrument_ids: dict, results: list):
    con.executemany(
        """
        INSERT INTO screener_results
            (screener_run_id, instrument_id, final_equity, sharpe, sortino, max_drawdown,
             win_rate, profit_factor, total_trades)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                screener_run_id, instrument_ids[r["symbol"]], r["metrics"]["final_equity"],
                r["metrics"]["sharpe"], r["metrics"]["sortino"], r["metrics"]["max_drawdown"],
                r["metrics"]["win_rate"], r["metrics"]["profit_factor"], r["metrics"]["total_trades"],
            )
            for r in results
        ],
    )


def list_screener_runs(con: sqlite3.Connection, limit: int = 50) -> list:
    rows = con.execute(
        """
        SELECT sr.id AS screener_run_id, sr.strategy_name AS strategy, sr.rank_by, sr.created_at,
               COUNT(res.id) AS n_results
        FROM screener_runs sr
        LEFT JOIN screener_results res ON res.screener_run_id = sr.id
        GROUP BY sr.id
        ORDER BY sr.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_screener_run(con: sqlite3.Connection, screener_run_id: int):
    run = con.execute("SELECT * FROM screener_runs WHERE id = ?", (screener_run_id,)).fetchone()
    if run is None:
        return None, []
    results = con.execute(
        """
        SELECT res.*, i.symbol, i.asset_class
        FROM screener_results res
        JOIN instruments i ON i.id = res.instrument_id
        WHERE res.screener_run_id = ?
        ORDER BY res.sharpe DESC
        """,
        (screener_run_id,),
    ).fetchall()
    return dict(run), [dict(r) for r in results]


# --- Sprint 6 -- portefeuille multi-actifs -----------------------------------

def create_portfolio_run(
    con: sqlite3.Connection, name: str, timeframe: str, initial_capital: float,
    rebalance: str, engine: str,
) -> int:
    cur = con.execute(
        """
        INSERT INTO portfolio_runs (user_id, name, timeframe, initial_capital, rebalance, engine)
        VALUES (NULL, ?, ?, ?, ?, ?)
        """,
        (name, timeframe, initial_capital, rebalance, engine),
    )
    return cur.lastrowid


def insert_portfolio_legs(con: sqlite3.Connection, portfolio_run_id: int, instrument_ids: dict, legs: list):
    con.executemany(
        """
        INSERT INTO portfolio_legs
            (portfolio_run_id, instrument_id, strategy_name, params_json, weight, final_equity, sharpe)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                portfolio_run_id, instrument_ids[leg["symbol"]], leg["strategy"],
                json.dumps(leg["params"]), leg["weight"],
                leg["metrics"]["final_equity"], leg["metrics"]["sharpe"],
            )
            for leg in legs
        ],
    )


def insert_portfolio_equity_curve(con: sqlite3.Connection, portfolio_run_id: int, equity_curve):
    con.executemany(
        "INSERT INTO portfolio_equity_curve_points (portfolio_run_id, timestamp, equity) VALUES (?, ?, ?)",
        [
            (portfolio_run_id, str(ts), float(eq))
            for ts, eq in zip(equity_curve["timestamp"], equity_curve["equity"])
        ],
    )


def list_portfolio_runs(con: sqlite3.Connection, limit: int = 50) -> list:
    rows = con.execute(
        """
        SELECT pr.id AS portfolio_run_id, pr.name, pr.created_at, COUNT(pl.id) AS n_legs,
               MAX(pep.equity) AS final_equity
        FROM portfolio_runs pr
        LEFT JOIN portfolio_legs pl ON pl.portfolio_run_id = pr.id
        LEFT JOIN portfolio_equity_curve_points pep ON pep.portfolio_run_id = pr.id
        GROUP BY pr.id
        ORDER BY pr.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_portfolio_run(con: sqlite3.Connection, portfolio_run_id: int):
    run = con.execute("SELECT * FROM portfolio_runs WHERE id = ?", (portfolio_run_id,)).fetchone()
    if run is None:
        return None, [], []
    legs = con.execute(
        """
        SELECT pl.*, i.symbol, i.asset_class
        FROM portfolio_legs pl
        JOIN instruments i ON i.id = pl.instrument_id
        WHERE pl.portfolio_run_id = ?
        """,
        (portfolio_run_id,),
    ).fetchall()
    curve = con.execute(
        "SELECT timestamp, equity FROM portfolio_equity_curve_points WHERE portfolio_run_id = ? ORDER BY timestamp",
        (portfolio_run_id,),
    ).fetchall()
    return dict(run), [dict(l) for l in legs], [dict(c) for c in curve]

    # --- Sprint 7 -- stratégies custom utilisateur ------------------------------

def create_custom_strategy(con: sqlite3.Connection, name: str, description: str) -> int:
    """Crée l'entrée `strategies` (type='custom_code') -- le code lui-même
    vit dans `strategy_code`, versionné, jamais dans `strategies.rules_json`
    (contrairement aux stratégies internes, où rules_json suffit)."""
    return create_strategy(
        con, name=name, description=description, rules_json="{}",
        type_="custom_code", language="python",
    )


def save_strategy_code(con: sqlite3.Connection, strategy_id: int, code: str, mode: str) -> int:
    """Insère une nouvelle version de code pour une stratégie custom
    existante -- ne remplace jamais une version précédente (voir schéma :
    UNIQUE(strategy_id, version), version = MAX(version) + 1)."""
    row = con.execute(
        "SELECT COALESCE(MAX(version), 0) AS max_version FROM strategy_code WHERE strategy_id = ?",
        (strategy_id,),
    ).fetchone()
    next_version = row["max_version"] + 1
    cur = con.execute(
        "INSERT INTO strategy_code (strategy_id, code, mode, version) VALUES (?, ?, ?, ?)",
        (strategy_id, code, mode, next_version),
    )
    con.execute("UPDATE strategies SET updated_at = datetime('now') WHERE id = ?", (strategy_id,))
    return cur.lastrowid


def get_latest_strategy_code(con: sqlite3.Connection, strategy_id: int):
    row = con.execute(
        "SELECT * FROM strategy_code WHERE strategy_id = ? ORDER BY version DESC LIMIT 1",
        (strategy_id,),
    ).fetchone()
    return dict(row) if row else None


def get_strategy_code_version(con: sqlite3.Connection, strategy_id: int, version: int):
    row = con.execute(
        "SELECT * FROM strategy_code WHERE strategy_id = ? AND version = ?",
        (strategy_id, version),
    ).fetchone()
    return dict(row) if row else None


def list_custom_strategies(con: sqlite3.Connection, limit: int = 50) -> list:
    rows = con.execute(
        """
        SELECT s.id AS strategy_id, s.name, s.description, s.created_at, s.updated_at,
               MAX(sc.version) AS latest_version, sc2.mode AS latest_mode
        FROM strategies s
        JOIN strategy_code sc ON sc.strategy_id = s.id
        LEFT JOIN strategy_code sc2 ON sc2.strategy_id = s.id AND sc2.version = (
            SELECT MAX(version) FROM strategy_code WHERE strategy_id = s.id
        )
        WHERE s.type = 'custom_code'
        GROUP BY s.id
        ORDER BY s.updated_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_custom_strategy(con: sqlite3.Connection, strategy_id: int):
    row = con.execute(
        "SELECT * FROM strategies WHERE id = ? AND type = 'custom_code'", (strategy_id,)
    ).fetchone()
    if row is None:
        return None, []
    versions = con.execute(
        "SELECT id, mode, version, created_at FROM strategy_code "
        "WHERE strategy_id = ? ORDER BY version DESC",
        (strategy_id,),
    ).fetchall()
    return dict(row), [dict(v) for v in versions]


def log_strategy_execution(
    con: sqlite3.Connection, strategy_code_id: int, kind: str, status: str,
    stdout: str, stderr: str, execution_time_ms: int, run_id: int = None,
) -> int:
    cur = con.execute(
        """
        INSERT INTO strategy_execution_logs
            (run_id, strategy_code_id, kind, status, stdout, stderr, execution_time_ms)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (run_id, strategy_code_id, kind, status, stdout, stderr, execution_time_ms),
    )
    return cur.lastrowid


def list_strategy_execution_logs(con: sqlite3.Connection, strategy_id: int, limit: int = 20) -> list:
    rows = con.execute(
        """
        SELECT sel.*, sc.version
        FROM strategy_execution_logs sel
        JOIN strategy_code sc ON sc.id = sel.strategy_code_id
        WHERE sc.strategy_id = ?
        ORDER BY sel.created_at DESC
        LIMIT ?
        """,
        (strategy_id, limit),
    ).fetchall()
    return [dict(r) for r in rows]