"""
Sprint 6 — Comparateur de stratégies.

Lance plusieurs variantes (stratégie + paramètres + moteur, jusqu'à 8 — voir
schemas.CompareRequest) sur le même instrument et la même fenêtre temporelle,
pour comparer leurs courbes d'equity et métriques côte à côte.

Pas de nouvelle table SQLite : chaque variante EST un backtest complet, déjà
persisté normalement via apps/api/backtests.run_and_persist_backtest (réutilisé
tel quel, aucune duplication de logique). Le comparateur n'est qu'une couche
d'orchestration au-dessus — on retrouve chaque variante individuellement dans
l'historique des backtests si besoin.
"""
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
            # Une variante invalide (ex. paramètre inconnu) ne fait pas
            # échouer toute la comparaison si d'autres variantes sont valides.
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