"""
Sprint 5 — Endpoints de lancement et consultation de backtests.

Relie l'entrepôt (via warehouse_reader), le moteur vectorisé (Sprint 4) et
la persistance SQLite (db.py). C'est le seul endroit du projet où ces trois
couches se rencontrent — le moteur lui-même reste inchangé depuis le Sprint 4
et ignore tout de FastAPI/SQLite.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from engine_vectorized import run_backtest  # noqa: E402
from metrics import compute_metrics  # noqa: E402
from strategies import rsi_mean_reversion, sma_crossover  # noqa: E402
from warehouse_reader import load_ohlcv  # noqa: E402

from .db import (  # noqa: E402
    create_backtest_run,
    create_strategy,
    get_connection,
    get_or_create_instrument,
    insert_backtest_result,
    insert_equity_curve,
    insert_trades,
)
from .schemas import BacktestRequest, BacktestResultOut, BacktestSummaryOut  # noqa: E402

router = APIRouter()

# Registre des stratégies disponibles — ajouter une entrée ici suffit à
# l'exposer via l'API (pas de changement ailleurs nécessaire).
STRATEGY_REGISTRY = {
    "sma_crossover": {
        "fn": sma_crossover,
        "default_params": {"fast": 20, "slow": 50},
        "label": "Croisement de moyennes mobiles",
    },
    "rsi_mean_reversion": {
        "fn": rsi_mean_reversion,
        "default_params": {"length": 14, "oversold": 30, "overbought": 70},
        "label": "Retour à la moyenne (RSI)",
    },
}


def _sanitize_metrics(metrics: dict) -> dict:
    """JSON standard ne supporte pas Infinity — remplacé par None (arrive
    quand une stratégie n'a aucun trade perdant, profit factor infini)."""
    m = dict(metrics)
    if m["profit_factor"] == float("inf"):
        m["profit_factor"] = None
    return m


@router.post("/backtests", response_model=BacktestResultOut)
def create_backtest_endpoint(req: BacktestRequest):
    if req.strategy not in STRATEGY_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {req.strategy}")

    spec = STRATEGY_REGISTRY[req.strategy]
    unknown_params = set(req.params) - set(spec["default_params"])
    if unknown_params:
        raise HTTPException(
            status_code=400,
            detail=f"Paramètre(s) inconnu(s) pour {req.strategy} : {', '.join(sorted(unknown_params))}. "
                   f"Paramètres attendus : {', '.join(spec['default_params'])}",
        )
    params = {**spec["default_params"], **req.params}

    try:
        df = load_ohlcv(req.symbol, req.asset_class, start=req.start_date, end=req.end_date)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    positions = spec["fn"](df, **params)
    result = run_backtest(
        df, positions,
        initial_capital=req.initial_capital,
        commission=req.commission,
        slippage=req.slippage,
    )
    metrics = _sanitize_metrics(
        compute_metrics(result["equity_curve"], result["trades"], req.initial_capital)
    )

    actual_start = str(df["timestamp"].min())
    actual_end = str(df["timestamp"].max())

    con = get_connection()
    try:
        instrument_id = get_or_create_instrument(con, req.symbol, req.asset_class)
        strategy_id = create_strategy(
            con, name=spec["label"], description=None,
            rules_json=json.dumps({"strategy": req.strategy, "params": params}),
        )
        run_id = create_backtest_run(
            con, strategy_id, instrument_id, timeframe="1d",
            start_date=actual_start, end_date=actual_end,
            initial_capital=req.initial_capital, commission=req.commission,
            slippage=req.slippage, params_json=json.dumps(params),
        )
        insert_backtest_result(con, run_id, metrics)
        insert_trades(con, run_id, instrument_id, result["trades"])
        insert_equity_curve(con, run_id, result["equity_curve"])
        con.commit()
    finally:
        con.close()

    return BacktestResultOut(
        run_id=run_id,
        symbol=req.symbol,
        asset_class=req.asset_class,
        strategy=req.strategy,
        params=params,
        start_date=actual_start,
        end_date=actual_end,
        initial_capital=req.initial_capital,
        metrics=metrics,
        equity_curve=[
            {"timestamp": str(ts), "equity": float(eq)}
            for ts, eq in zip(result["equity_curve"]["timestamp"], result["equity_curve"]["equity"])
        ],
        trades=[
            {**t, "entry_time": str(t["entry_time"]), "exit_time": str(t["exit_time"])}
            for t in result["trades"]
        ],
    )


@router.get("/backtests", response_model=list[BacktestSummaryOut])
def list_backtests(limit: int = 50):
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT br.id AS run_id, i.symbol, s.name AS strategy, br.created_at,
                   res.final_equity, res.sharpe, res.total_trades
            FROM backtest_runs br
            JOIN instruments i ON i.id = br.instrument_id
            JOIN strategies s ON s.id = br.strategy_id
            LEFT JOIN backtest_results res ON res.run_id = br.id
            ORDER BY br.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    finally:
        con.close()
    return [dict(r) for r in rows]


@router.get("/backtests/{run_id}", response_model=BacktestResultOut)
def get_backtest(run_id: int):
    con = get_connection()
    try:
        run = con.execute(
            """
            SELECT br.*, i.symbol, i.asset_class, s.name AS strategy_name, s.rules_json
            FROM backtest_runs br
            JOIN instruments i ON i.id = br.instrument_id
            JOIN strategies s ON s.id = br.strategy_id
            WHERE br.id = ?
            """,
            (run_id,),
        ).fetchone()
        if run is None:
            raise HTTPException(status_code=404, detail=f"Backtest {run_id} introuvable")

        result_row = con.execute(
            "SELECT * FROM backtest_results WHERE run_id = ?", (run_id,)
        ).fetchone()
        trades_rows = con.execute(
            "SELECT * FROM trades WHERE run_id = ? ORDER BY entry_time", (run_id,)
        ).fetchall()
        equity_rows = con.execute(
            "SELECT timestamp, equity FROM equity_curve_points WHERE run_id = ? ORDER BY timestamp",
            (run_id,),
        ).fetchall()
    finally:
        con.close()

    rules = json.loads(run["rules_json"])
    metrics = dict(result_row) if result_row else {}

    return BacktestResultOut(
        run_id=run["id"],
        symbol=run["symbol"],
        asset_class=run["asset_class"],
        strategy=rules.get("strategy", run["strategy_name"]),
        params=rules.get("params", {}),
        start_date=run["start_date"],
        end_date=run["end_date"],
        initial_capital=run["initial_capital"],
        metrics=metrics,
        equity_curve=[{"timestamp": r["timestamp"], "equity": r["equity"]} for r in equity_rows],
        trades=[
            {
                "entry_time": r["entry_time"], "entry_price": r["entry_price"],
                "exit_time": r["exit_time"], "exit_price": r["exit_price"],
                "quantity": r["quantity"], "side": r["side"], "pnl": r["pnl"],
            }
            for r in trades_rows
        ],
    )