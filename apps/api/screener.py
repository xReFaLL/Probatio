"""
Sprint 6 — Endpoints du screener.

Croise l'univers d'instruments réellement disponible dans l'entrepôt (même
logique que apps/api/instruments.py) avec packages/backtest-engine/screener.py
pour scanner plusieurs instruments avec une même stratégie/paramètres, puis
persiste le classement (tables screener_runs / screener_results).
"""
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from screener import run_screener  # noqa: E402
from strategies import rsi_mean_reversion, sma_crossover  # noqa: E402

from .db import (  # noqa: E402
    create_screener_run,
    get_connection,
    get_or_create_instrument,
    get_screener_run,
    insert_screener_results,
    list_screener_runs,
)
from .instruments import list_available_instruments  # noqa: E402
from .schemas import ScreenerRequest, ScreenerResultOut, ScreenerSummaryOut  # noqa: E402

router = APIRouter()

STRATEGY_FNS = {"sma_crossover": sma_crossover, "rsi_mean_reversion": rsi_mean_reversion}


def _resolve_instruments(req: ScreenerRequest) -> list:
    available = list_available_instruments()
    if req.symbols:
        wanted = set(req.symbols)
        available = [i for i in available if i["symbol"] in wanted]
    if req.asset_class:
        available = [i for i in available if i["asset_class"] == req.asset_class]
    return available


@router.post("/screener", response_model=ScreenerResultOut)
def create_screener_endpoint(req: ScreenerRequest):
    if req.strategy not in STRATEGY_FNS:
        raise HTTPException(status_code=400, detail=f"Stratégie inconnue : {req.strategy}")

    instruments = _resolve_instruments(req)
    if not instruments:
        raise HTTPException(
            status_code=404,
            detail="Aucun instrument disponible pour ces critères (asset_class/symbols) dans l'entrepôt.",
        )

    try:
        outcome = run_screener(
            instruments=instruments,
            strategy_fn=STRATEGY_FNS[req.strategy],
            params=req.params,
            start=req.start_date,
            end=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
            slippage=req.slippage,
            engine=req.engine,
            position_size=req.position_size,
            rank_by=req.rank_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    con = get_connection()
    try:
        instrument_ids = {
            r["symbol"]: get_or_create_instrument(con, r["symbol"], r["asset_class"])
            for r in outcome["results"]
        }
        screener_run_id = create_screener_run(
            con,
            strategy_name=req.strategy,
            params_json=json.dumps(req.params),
            asset_class=req.asset_class,
            timeframe="1d",
            rank_by=req.rank_by,
        )
        insert_screener_results(con, screener_run_id, instrument_ids, outcome["results"])
        con.commit()
    finally:
        con.close()

    return ScreenerResultOut(
        screener_run_id=screener_run_id,
        strategy=req.strategy,
        params=req.params,
        rank_by=req.rank_by,
        results=outcome["results"],
        skipped=outcome["skipped"],
    )


@router.get("/screener", response_model=list[ScreenerSummaryOut])
def list_screener_endpoint(limit: int = 50):
    con = get_connection()
    try:
        return list_screener_runs(con, limit)
    finally:
        con.close()


@router.get("/screener/{screener_run_id}", response_model=ScreenerResultOut)
def get_screener_endpoint(screener_run_id: int):
    con = get_connection()
    try:
        run, results = get_screener_run(con, screener_run_id)
    finally:
        con.close()

    if run is None:
        raise HTTPException(status_code=404, detail=f"Screener run {screener_run_id} introuvable")

    return ScreenerResultOut(
        screener_run_id=run["id"],
        strategy=run["strategy_name"],
        params=json.loads(run["params_json"]),
        rank_by=run["rank_by"],
        results=[
            {
                "symbol": r["symbol"],
                "asset_class": r["asset_class"],
                "metrics": {
                    "final_equity": r["final_equity"],
                    "sharpe": r["sharpe"],
                    "sortino": r["sortino"],
                    "max_drawdown": r["max_drawdown"],
                    "win_rate": r["win_rate"],
                    "profit_factor": r["profit_factor"],
                    "total_trades": r["total_trades"],
                },
            }
            for r in results
        ],
        skipped=[],  # non persisté (voir screener_results) — uniquement disponible sur la réponse à chaud
    )