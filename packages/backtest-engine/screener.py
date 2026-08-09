"""
Sprint 6 — Screener : applique une même stratégie/paramètres à un univers
d'instruments et classe les résultats selon une métrique de performance.

Usage typique : "quels titres du S&P 500 auraient le mieux répondu à un
croisement de moyennes mobiles (20/50) sur les 5 dernières années ?"

Chaque instrument est backtesté indépendamment (même moteur, mêmes
paramètres, même fenêtre temporelle) — le screener ne fait qu'orchestrer
warehouse_reader + engine_*/metrics.compute_metrics en boucle et trier le
résultat. Un instrument sans données dans l'entrepôt (ou dont la stratégie
échoue, ex. historique trop court pour la période de warm-up d'un
indicateur) est écarté dans `skipped` avec la raison plutôt que de faire
échouer tout le scan.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_event_driven import run_backtest as run_backtest_event_driven  # noqa: E402
from engine_vectorized import run_backtest as run_backtest_vectorized  # noqa: E402
from metrics import compute_metrics  # noqa: E402
from warehouse_reader import load_ohlcv  # noqa: E402

ENGINES = {"vectorized": run_backtest_vectorized, "event_driven": run_backtest_event_driven}
RANKABLE_METRICS = {
    "sharpe", "sortino", "final_equity", "max_drawdown", "win_rate", "profit_factor", "total_trades",
}


def run_screener(
    instruments: list,
    strategy_fn,
    params: dict,
    timeframe: str = "1d",
    start: str = None,
    end: str = None,
    initial_capital: float = 10_000.0,
    commission: float = 0.0005,
    slippage: float = 0.0005,
    engine: str = "vectorized",
    position_size: float = 1.0,
    rank_by: str = "sharpe",
) -> dict:
    if rank_by not in RANKABLE_METRICS:
        raise ValueError(f"Métrique de classement non supportée : {rank_by}")
    if engine not in ENGINES:
        raise ValueError(f"Moteur inconnu : {engine}")

    run_engine = ENGINES[engine]
    engine_kwargs = {"commission": commission, "slippage": slippage}
    if engine == "event_driven":
        engine_kwargs["position_size"] = position_size

    results, skipped = [], []
    for inst in instruments:
        symbol, asset_class = inst["symbol"], inst["asset_class"]
        try:
            df = load_ohlcv(symbol, asset_class, timeframe=timeframe, start=start, end=end)
            positions = strategy_fn(df, **params)
            result = run_engine(df, positions, initial_capital=initial_capital, **engine_kwargs)
            m = compute_metrics(result["equity_curve"], result["trades"], initial_capital)
        except FileNotFoundError:
            skipped.append({
                "symbol": symbol, "asset_class": asset_class,
                "reason": "Aucune donnée dans l'entrepôt pour cet instrument.",
            })
            continue
        except Exception as e:  # ex. warm-up d'indicateur trop long pour l'historique dispo
            skipped.append({"symbol": symbol, "asset_class": asset_class, "reason": str(e)})
            continue

        if m.get("profit_factor") == float("inf"):
            m["profit_factor"] = None

        results.append({"symbol": symbol, "asset_class": asset_class, "metrics": m})

    def _sort_key(r):
        v = r["metrics"].get(rank_by)
        return v if v is not None else float("-inf")

    # Pour toutes les métriques du registre, une valeur plus élevée est
    # toujours préférable — y compris max_drawdown, qui est négatif ou nul :
    # -0.05 (peu de baisse) doit passer devant -0.30 (grosse baisse), donc
    # tri décroissant classique.
    results.sort(key=_sort_key, reverse=True)

    return {"results": results, "skipped": skipped, "rank_by": rank_by}