"""
Sprint 6 — Portefeuille multi-actifs.

Combine plusieurs backtests indépendants (une stratégie + un instrument par
"jambe" du portefeuille) en une seule courbe d'equity pondérée, pour évaluer
une allocation multi-actifs plutôt qu'un actif isolé.

Approche retenue (volontairement simple, cohérente avec un moteur "sur
mesure" plutôt qu'un simulateur de carnet d'ordres multi-actifs complet) :
chaque jambe est backtestée indépendamment avec le moteur vectorisé ou
event-driven habituel (commission/slippage déjà appliqués dans la courbe de
la jambe), puis les courbes d'equity normalisées sont recombinées hors
ligne :
  - `rebalance="none"` : le capital alloué à chaque jambe au départ suit sa
    propre courbe d'equity sans jamais être retouché (achat et conservation
    des stratégies elles-mêmes) — les poids dérivent naturellement dans le
    temps selon la performance relative des jambes ;
  - `rebalance="monthly"` / `"quarterly"` : à intervalle régulier, la valeur
    totale du portefeuille est redistribuée entre les jambes selon les poids
    cibles. Le coût de rebalancement lui-même (frais de vente/achat pour
    revenir aux poids cibles) est ignoré au Sprint 6 — piste d'amélioration
    future si besoin.

Chaque jambe garde son propre journal de trades (utile pour l'inspection),
mais la courbe d'equity globale exposée est celle du portefeuille recombiné.
Calendrier commun = union des dates de toutes les jambes ; une jambe sans
barre à une date donnée (désynchronisation de calendrier entre classes
d'actifs, ex. crypto 24/7 vs actions) garde sa dernière valeur connue plutôt
que de créer un trou dans le portefeuille.
"""
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
_REBALANCE_DAYS = {"none": None, "monthly": 30, "quarterly": 91}


def run_portfolio(
    legs: list,
    strategy_registry: dict,
    timeframe: str = "1d",
    start: str = None,
    end: str = None,
    initial_capital: float = 10_000.0,
    commission: float = 0.0005,
    slippage: float = 0.0005,
    engine: str = "vectorized",
    position_size: float = 1.0,
    rebalance: str = "none",
) -> dict:
    if not legs:
        raise ValueError("Le portefeuille doit contenir au moins une jambe.")
    if engine not in ENGINES:
        raise ValueError(f"Moteur inconnu : {engine}")
    if rebalance not in _REBALANCE_DAYS:
        raise ValueError(f"Mode de rebalancement non supporté : {rebalance}")

    total_weight = sum(leg["weight"] for leg in legs)
    if total_weight <= 0:
        raise ValueError("La somme des poids des jambes doit être positive.")

    run_engine = ENGINES[engine]
    engine_kwargs = {"commission": commission, "slippage": slippage}
    if engine == "event_driven":
        engine_kwargs["position_size"] = position_size

    leg_results = []
    for leg in legs:
        weight = leg["weight"] / total_weight
        spec = strategy_registry[leg["strategy"]]
        try:
            df = load_ohlcv(leg["symbol"], leg["asset_class"], timeframe=timeframe, start=start, end=end)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Jambe {leg['symbol']} : {e}") from e

        params = {**spec["default_params"], **leg.get("params", {})}
        positions = spec["fn"](df, **params)
        result = run_engine(df, positions, initial_capital=initial_capital, **engine_kwargs)
        m = compute_metrics(result["equity_curve"], result["trades"], initial_capital)
        if m.get("profit_factor") == float("inf"):
            m["profit_factor"] = None

        curve = result["equity_curve"].copy()
        curve["timestamp"] = pd.to_datetime(curve["timestamp"])
        leg_results.append({
            "symbol": leg["symbol"], "asset_class": leg["asset_class"], "strategy": leg["strategy"],
            "params": params, "weight": weight,
            "curve": curve.set_index("timestamp")["equity"],
            "trades": result["trades"], "metrics": m,
        })

    all_index = sorted(set().union(*[set(lr["curve"].index) for lr in leg_results]))
    calendar = pd.Index(all_index, name="timestamp")

    normalized = {}
    for lr in leg_results:
        s = lr["curve"].reindex(calendar).ffill().bfill()
        normalized[f"{lr['symbol']}::{lr['strategy']}"] = s / s.iloc[0]
    norm_df = pd.DataFrame(normalized)

    rebalance_every = _REBALANCE_DAYS[rebalance]
    n = len(calendar)
    weights = np.array([lr["weight"] for lr in leg_results], dtype=np.float64)
    shares = weights * initial_capital  # capital alloué à chaque jambe au dernier point de référence

    portfolio_equity = np.empty(n, dtype=np.float64)
    last_rebalance_i = 0
    for i in range(n):
        values = shares * norm_df.iloc[i].to_numpy()
        portfolio_equity[i] = float(values.sum())
        if rebalance_every and (calendar[i] - calendar[last_rebalance_i]).days >= rebalance_every:
            # Nouvelles parts détenues par jambe = valeur cible (poids * valeur
            # totale du portefeuille) convertie en "unités" de la courbe
            # normalisée de la jambe à l'instant du rebalancement. Diviser par
            # norm_df.iloc[i] est essentiel : sans cela, les parts sont
            # réinjectées comme si la courbe normalisée repartait de 1 à
            # chaque rebalancement, ce qui compose la performance déjà
            # accumulée en plus de la nouvelle — explosion artificielle du
            # portefeuille dès le deuxième rebalancement.
            shares = weights * portfolio_equity[i] / norm_df.iloc[i].to_numpy()
            last_rebalance_i = i

    portfolio_curve = pd.DataFrame({"timestamp": calendar.astype(str), "equity": portfolio_equity})
    all_trades = [{**t, "symbol": lr["symbol"]} for lr in leg_results for t in lr["trades"]]

    aggregate_metrics = compute_metrics(portfolio_curve, all_trades, initial_capital)
    if aggregate_metrics.get("profit_factor") == float("inf"):
        aggregate_metrics["profit_factor"] = None

    return {
        "legs": [
            {
                "symbol": lr["symbol"], "asset_class": lr["asset_class"], "strategy": lr["strategy"],
                "params": lr["params"], "weight": lr["weight"], "metrics": lr["metrics"],
            }
            for lr in leg_results
        ],
        "portfolio_equity_curve": portfolio_curve,
        "aggregate_metrics": aggregate_metrics,
        "final_equity": float(portfolio_equity[-1]) if n else initial_capital,
    }