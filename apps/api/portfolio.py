"""
Sprint 6 — Endpoints du portefeuille multi-actifs.

Relie packages/backtest-engine/portfolio.py (combinaison des courbes
d'equity par jambe) à la persistance SQLite (tables portfolio_runs /
portfolio_legs / portfolio_equity_curve_points).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from portfolio import run_portfolio  # noqa: E402
from strategies import rsi_mean_reversion, sma_crossover  # noqa: E402

from .db import (  # noqa: E402
    create_portfolio_run,
    get_connection,
    get_or_create_instrument,
    get_portfolio_run,
    insert_portfolio_equity_curve,
    insert_portfolio_legs,
    list_portfolio_runs,
)
from .schemas import PortfolioRequest, PortfolioResultOut, PortfolioSummaryOut  # noqa: E402

router = APIRouter()

# Même registre que backtests.STRATEGY_REGISTRY (dupliqué volontairement,
# pas d'import croisé entre routers pour garder chaque fichier autonome —
# voir backtests.py si une entrée doit être ajoutée, à répercuter ici).
STRATEGY_REGISTRY = {
    "sma_crossover": {"fn": sma_crossover, "default_params": {"fast": 20, "slow": 50}},
    "rsi_mean_reversion": {"fn": rsi_mean_reversion, "default_params": {"length": 14, "oversold": 30, "overbought": 70}},
}


@router.post("/portfolio", response_model=PortfolioResultOut)
def create_portfolio_endpoint(req: PortfolioRequest):
    for leg in req.legs:
        if leg.strategy not in STRATEGY_REGISTRY:
            raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {leg.strategy}")

    legs_payload = [
        {
            "symbol": leg.symbol, "asset_class": leg.asset_class,
            "strategy": leg.strategy, "params": leg.params, "weight": leg.weight,
        }
        for leg in req.legs
    ]

    try:
        outcome = run_portfolio(
            legs=legs_payload,
            strategy_registry=STRATEGY_REGISTRY,
            start=req.start_date,
            end=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
            slippage=req.slippage,
            engine=req.engine,
            position_size=req.position_size,
            rebalance=req.rebalance,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    con = get_connection()
    try:
        instrument_ids = {
            leg["symbol"]: get_or_create_instrument(con, leg["symbol"], leg["asset_class"])
            for leg in outcome["legs"]
        }
        portfolio_run_id = create_portfolio_run(
            con, name=req.name, timeframe="1d", initial_capital=req.initial_capital,
            rebalance=req.rebalance, engine=req.engine,
        )
        insert_portfolio_legs(con, portfolio_run_id, instrument_ids, outcome["legs"])
        insert_portfolio_equity_curve(con, portfolio_run_id, outcome["portfolio_equity_curve"])
        con.commit()
    finally:
        con.close()

    curve = outcome["portfolio_equity_curve"]
    return PortfolioResultOut(
        portfolio_run_id=portfolio_run_id,
        name=req.name,
        rebalance=req.rebalance,
        legs=outcome["legs"],
        aggregate_metrics=outcome["aggregate_metrics"],
        equity_curve=[
            {"timestamp": str(ts), "equity": float(eq)}
            for ts, eq in zip(curve["timestamp"], curve["equity"])
        ],
    )


@router.get("/portfolio", response_model=list[PortfolioSummaryOut])
def list_portfolio_endpoint(limit: int = 50):
    con = get_connection()
    try:
        return list_portfolio_runs(con, limit)
    finally:
        con.close()


@router.get("/portfolio/{portfolio_run_id}", response_model=PortfolioResultOut)
def get_portfolio_endpoint(portfolio_run_id: int):
    con = get_connection()
    try:
        run, legs, curve = get_portfolio_run(con, portfolio_run_id)
    finally:
        con.close()

    if run is None:
        raise HTTPException(status_code=404, detail=f"Portfolio run {portfolio_run_id} introuvable")

    return PortfolioResultOut(
        portfolio_run_id=run["id"],
        name=run["name"],
        rebalance=run["rebalance"],
        legs=[
            {
                "symbol": leg["symbol"],
                "asset_class": leg["asset_class"],
                "strategy": leg["strategy_name"],
                "params": json.loads(leg["params_json"]),
                "weight": leg["weight"],
                "metrics": {
                    "final_equity": leg["final_equity"], "sharpe": leg["sharpe"],
                    "sortino": 0.0, "max_drawdown": 0.0, "win_rate": 0.0,
                    "profit_factor": None, "total_trades": 0,
                },
            }
            for leg in legs
        ],
        aggregate_metrics={
            "final_equity": curve[-1]["equity"] if curve else run["initial_capital"],
            "sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0, "win_rate": 0.0,
            "profit_factor": None, "total_trades": 0,
        },
        equity_curve=[{"timestamp": c["timestamp"], "equity": c["equity"]} for c in curve],
    )