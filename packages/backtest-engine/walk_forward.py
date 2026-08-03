"""
Sprint 6 — Walk-forward analysis.

Découpe l'historique en fenêtres glissantes in-sample / out-of-sample. Sur
chaque fenêtre in-sample, recherche par grille (grid search) les meilleurs
paramètres de la stratégie selon une métrique cible (Sharpe par défaut),
puis applique ces paramètres tels quels sur la fenêtre out-of-sample
suivante (jamais vue pendant l'optimisation) pour mesurer une performance
hors échantillon. Les fenêtres avancent ensuite d'un pas (`step_bars`,
= out_sample_bars par défaut) jusqu'à épuisement de l'historique.

La courbe "walk-forward" retournée est la concaténation, bout à bout, des
segments d'equity out-of-sample de chaque fenêtre (le capital de fin de
fenêtre devient le capital de départ de la fenêtre suivante) — c'est la
meilleure estimation disponible de ce qu'aurait vécu un trader ré-optimisant
périodiquement sa stratégie sans jamais connaître le futur.

Aucun accès réseau/disque ici en dehors de warehouse_reader.load_ohlcv
(chargé une seule fois pour tout l'historique, puis tranché en mémoire).
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine_event_driven import run_backtest as run_backtest_event_driven  # noqa: E402
from engine_vectorized import run_backtest as run_backtest_vectorized  # noqa: E402
from metrics import compute_metrics  # noqa: E402
from warehouse_reader import load_ohlcv  # noqa: E402

ENGINES = {"vectorized": run_backtest_vectorized, "event_driven": run_backtest_event_driven}
OPTIMIZE_METRICS = {"sharpe", "sortino", "profit_factor", "final_equity"}


def _param_grid(param_grid: dict) -> list:
    """Transforme {"fast": [10, 20], "slow": 50} en toutes les combinaisons
    du produit cartésien. Une valeur scalaire (pas une liste) est traitée
    comme une grille à un seul point."""
    if not param_grid:
        return [{}]
    keys = list(param_grid)
    values = [v if isinstance(v, list) else [v] for v in param_grid.values()]
    return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


def _sanitize(m: dict) -> dict:
    out = dict(m)
    if out.get("profit_factor") == float("inf"):
        out["profit_factor"] = None
    return out


def run_walk_forward(
    symbol: str,
    asset_class: str,
    strategy_fn,
    param_grid: dict,
    timeframe: str = "1d",
    start: str = None,
    end: str = None,
    in_sample_bars: int = 504,
    out_sample_bars: int = 126,
    step_bars: int = None,
    optimize_metric: str = "sharpe",
    initial_capital: float = 10_000.0,
    commission: float = 0.0005,
    slippage: float = 0.0005,
    engine: str = "vectorized",
    position_size: float = 1.0,
) -> dict:
    if optimize_metric not in OPTIMIZE_METRICS:
        raise ValueError(f"Métrique d'optimisation non supportée : {optimize_metric}")
    if engine not in ENGINES:
        raise ValueError(f"Moteur inconnu : {engine}")

    run_engine = ENGINES[engine]
    engine_kwargs = {"commission": commission, "slippage": slippage}
    if engine == "event_driven":
        engine_kwargs["position_size"] = position_size

    step_bars = step_bars or out_sample_bars
    if step_bars <= 0 or in_sample_bars <= 0 or out_sample_bars <= 0:
        raise ValueError("in_sample_bars, out_sample_bars et step_bars doivent être positifs.")

    df = load_ohlcv(symbol, asset_class, timeframe=timeframe, start=start, end=end)
    n = len(df)
    if n < in_sample_bars + out_sample_bars:
        raise ValueError(
            f"Historique trop court ({n} barres) pour in_sample_bars={in_sample_bars} + "
            f"out_sample_bars={out_sample_bars}. Réduis ces fenêtres ou élargis la plage de dates."
        )

    combos = _param_grid(param_grid)

    windows = []
    stitched_frames = []
    all_oos_trades = []
    running_capital = initial_capital

    is_start_idx = 0
    while is_start_idx + in_sample_bars + out_sample_bars <= n:
        is_slice = df.iloc[is_start_idx: is_start_idx + in_sample_bars].reset_index(drop=True)
        oos_slice = df.iloc[
            is_start_idx + in_sample_bars: is_start_idx + in_sample_bars + out_sample_bars
        ].reset_index(drop=True)

        best_params, best_score = None, None
        for params in combos:
            try:
                is_positions = strategy_fn(is_slice, **params)
                is_result = run_engine(is_slice, is_positions, initial_capital=initial_capital, **engine_kwargs)
                m = compute_metrics(is_result["equity_curve"], is_result["trades"], initial_capital)
            except Exception:
                continue
            score = m.get(optimize_metric)
            if score is None or (isinstance(score, float) and np.isnan(score)):
                continue
            score = 1e12 if score == float("inf") else score
            if best_score is None or score > best_score:
                best_score, best_params = score, params

        # Aucune combinaison exploitable (données insuffisantes pour l'indicateur,
        # etc.) -> on retient quand même la première combinaison de la grille par
        # défaut plutôt que de faire échouer toute l'analyse pour une fenêtre.
        if best_params is None:
            best_params, best_score = combos[0], 0.0

        oos_positions = strategy_fn(oos_slice, **best_params)
        oos_result = run_engine(oos_slice, oos_positions, initial_capital=running_capital, **engine_kwargs)
        oos_metrics = _sanitize(
            compute_metrics(oos_result["equity_curve"], oos_result["trades"], running_capital)
        )

        windows.append({
            "window_index": len(windows),
            "is_start": str(is_slice["timestamp"].iloc[0]),
            "is_end": str(is_slice["timestamp"].iloc[-1]),
            "oos_start": str(oos_slice["timestamp"].iloc[0]),
            "oos_end": str(oos_slice["timestamp"].iloc[-1]),
            "best_params": best_params,
            "is_score": float(best_score),
            "oos_metrics": oos_metrics,
        })

        stitched_frames.append(oos_result["equity_curve"])
        all_oos_trades.extend(oos_result["trades"])
        running_capital = oos_result["final_equity"]

        is_start_idx += step_bars

    stitched_equity = (
        pd.concat(stitched_frames, ignore_index=True)
        if stitched_frames
        else pd.DataFrame(columns=["timestamp", "equity"])
    )

    # Bug corrigé : l'agrégat était auparavant calculé avec une liste de
    # trades vide, ce qui forçait win_rate et profit_factor à zéro quel que
    # soit le vrai résultat (sharpe/sortino/max_drawdown/final_equity, eux,
    # dépendent uniquement de stitched_equity et n'étaient pas affectés).
    # En passant les vrais trades OOS de toutes les fenêtres, compute_metrics
    # calcule un win_rate/profit_factor agrégé correct -- total_trades tombe
    # juste automatiquement aussi, plus besoin de le recalculer à part.
    aggregate_metrics = (
        _sanitize(compute_metrics(stitched_equity, all_oos_trades, initial_capital))
        if len(stitched_equity)
        else {
            "final_equity": initial_capital, "sharpe": 0.0, "sortino": 0.0,
            "max_drawdown": 0.0, "win_rate": 0.0, "profit_factor": None, "total_trades": 0,
        }
    )

    return {
        "windows": windows,
        "stitched_equity_curve": stitched_equity,
        "aggregate_metrics": aggregate_metrics,
        "n_windows": len(windows),
    }