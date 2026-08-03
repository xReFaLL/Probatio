"""
Sprint 6 — Endpoints de walk-forward analysis.

Relie l'entrepôt (via warehouse_reader, importé indirectement par
packages/backtest-engine/walk_forward.py), la logique de fenêtrage
in-sample/out-of-sample (walk_forward.run_walk_forward) et la persistance
SQLite (db.py, tables walk_forward_runs / walk_forward_windows).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from strategies import rsi_mean_reversion, sma_crossover  # noqa: E402
from walk_forward import run_walk_forward  # noqa: E402

from .db import (  # noqa: E402
    create_walk_forward_run,
    get_connection,
    get_or_create_instrument,
    get_walk_forward_run,
    insert_walk_forward_windows,
    list_walk_forward_runs,
)
from .schemas import WalkForwardRequest, WalkForwardResultOut, WalkForwardSummaryOut  # noqa: E402

router = APIRouter()

# Même registre de stratégies que backtests.py, réduit aux fonctions (le
# walk-forward n'a pas besoin des default_params : chaque combinaison de la
# grille founie par l'utilisateur est testée telle quelle).
STRATEGY_FNS = {"sma_crossover": sma_crossover, "rsi_mean_reversion": rsi_mean_reversion}


def _sanitize_metrics(m: dict) -> dict:
    m = dict(m)
    if m.get("profit_factor") == float("inf"):
        m["profit_factor"] = None
    return m


@router.post("/walk-forward", response_model=WalkForwardResultOut)
def create_walk_forward_endpoint(req: WalkForwardRequest):
    if req.strategy not in STRATEGY_FNS:
        raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {req.strategy}")

    try:
        result = run_walk_forward(
            symbol=req.symbol,
            asset_class=req.asset_class,
            strategy_fn=STRATEGY_FNS[req.strategy],
            param_grid=req.param_grid,
            start=req.start_date,
            end=req.end_date,
            in_sample_bars=req.in_sample_bars,
            out_sample_bars=req.out_sample_bars,
            step_bars=req.step_bars,
            optimize_metric=req.optimize_metric,
            initial_capital=req.initial_capital,
            commission=req.commission,
            slippage=req.slippage,
            engine=req.engine,
            position_size=req.position_size,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    con = get_connection()
    try:
        instrument_id = get_or_create_instrument(con, req.symbol, req.asset_class)
        walk_forward_run_id = create_walk_forward_run(
            con,
            strategy_name=req.strategy,
            instrument_id=instrument_id,
            timeframe="1d",
            param_grid_json=json.dumps(req.param_grid),
            in_sample_bars=req.in_sample_bars,
            out_sample_bars=req.out_sample_bars,
            optimize_metric=req.optimize_metric,
            engine=req.engine,
        )
        insert_walk_forward_windows(con, walk_forward_run_id, result["windows"])
        con.commit()
    finally:
        con.close()

    curve = result["stitched_equity_curve"]
    return WalkForwardResultOut(
        walk_forward_run_id=walk_forward_run_id,
        symbol=req.symbol,
        asset_class=req.asset_class,
        strategy=req.strategy,
        optimize_metric=req.optimize_metric,
        n_windows=result["n_windows"],
        windows=result["windows"],
        aggregate_metrics=_sanitize_metrics(result["aggregate_metrics"]),
        stitched_equity_curve=[
            {"timestamp": str(ts), "equity": float(eq)}
            for ts, eq in zip(curve["timestamp"], curve["equity"])
        ],
    )


@router.get("/walk-forward", response_model=list[WalkForwardSummaryOut])
def list_walk_forward_endpoint(limit: int = 50):
    con = get_connection()
    try:
        return list_walk_forward_runs(con, limit)
    finally:
        con.close()


@router.get("/walk-forward/{walk_forward_run_id}", response_model=WalkForwardResultOut)
def get_walk_forward_endpoint(walk_forward_run_id: int):
    con = get_connection()
    try:
        run, windows = get_walk_forward_run(con, walk_forward_run_id)
    finally:
        con.close()

    if run is None:
        raise HTTPException(status_code=404, detail=f"Walk-forward run {walk_forward_run_id} introuvable")

    window_items = [
        {
            "window_index": w["window_index"],
            "is_start": w["is_start"],
            "is_end": w["is_end"],
            "oos_start": w["oos_start"],
            "oos_end": w["oos_end"],
            "best_params": json.loads(w["best_params_json"]),
            "is_score": w["is_score"] or 0.0,
            "oos_metrics": {
                "final_equity": w["oos_final_equity"] or 0.0,
                "sharpe": w["oos_sharpe"] or 0.0,
                "sortino": 0.0,  # non stocké en base au niveau fenêtre — voir note ci-dessous
                "max_drawdown": w["oos_max_drawdown"] or 0.0,
                "win_rate": 0.0,
                "profit_factor": None,
                "total_trades": w["oos_total_trades"] or 0,
            },
        }
        for w in windows
    ]
    total_trades = sum(w["oos_total_trades"] or 0 for w in windows)
    avg_sharpe = (
        sum(w["oos_sharpe"] or 0.0 for w in windows) / len(windows) if windows else 0.0
    )

    return WalkForwardResultOut(
        walk_forward_run_id=run["id"],
        symbol=run["symbol"],
        asset_class=run["asset_class"],
        strategy=run["strategy_name"],
        optimize_metric=run["optimize_metric"],
        n_windows=len(windows),
        windows=window_items,
        # Rechargement historique : reconstruit une approximation de
        # l'agrégat à partir des colonnes stockées par fenêtre (sortino,
        # win_rate et profit_factor détaillés ne sont pas persistés au
        # niveau fenêtre pour garder le schéma léger — recalcule un
        # walk-forward complet via POST /walk-forward pour le détail exact).
        aggregate_metrics={
            "final_equity": windows[-1]["oos_final_equity"] if windows else 0.0,
            "sharpe": avg_sharpe,
            "sortino": 0.0,
            "max_drawdown": min((w["oos_max_drawdown"] or 0.0 for w in windows), default=0.0),
            "win_rate": 0.0,
            "profit_factor": None,
            "total_trades": total_trades,
        },
        stitched_equity_curve=[],  # non reconstituée au rechargement — voir note ci-dessus
    )