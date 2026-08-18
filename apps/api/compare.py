
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "packages" / "data-pipeline"))
sys.path.insert(0, str(ROOT / "packages" / "backtest-engine"))

from fastapi import APIRouter, HTTPException  # noqa: E402

from .backtests import run_and_persist_backtest  # noqa: E402
from .schemas import BacktestRequest, CompareRequest, CompareResultOut  # noqa: E402

router = APIRouter()


@router.post("/compare", response_model=CompareResultOut)
def create_compare_endpoint(req: CompareRequest):
    variant_results = []
    errors = []
    for i, variant in enumerate(req.variants):
        backtest_req = BacktestRequest(
            symbol=req.symbol,
            asset_class=req.asset_class,
            strategy=variant.strategy,
            params=variant.params,
            start_date=req.start_date,
            end_date=req.end_date,
            initial_capital=req.initial_capital,
            commission=req.commission,
            slippage=req.slippage,
            engine=variant.engine,
            position_size=variant.position_size,
        )
        try:
            result = run_and_persist_backtest(backtest_req)
        except HTTPException as e:
            errors.append(f"Variante {i + 1} ({variant.label or variant.strategy}) : {e.detail}")
            continue

        label = variant.label or f"{variant.strategy} ({variant.engine})"
        variant_results.append({
            "label": label,
            "run_id": result.run_id,
            "strategy": result.strategy,
            "params": result.params,
            "engine": result.engine,
            "metrics": result.metrics,
            "equity_curve": result.equity_curve,
        })

    if not variant_results:
        raise HTTPException(status_code=400, detail="Aucune variante n'a pu être backtestée : " + " | ".join(errors))

    return CompareResultOut(symbol=req.symbol, asset_class=req.asset_class, variants=variant_results)