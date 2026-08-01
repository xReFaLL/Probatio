"""
Sprint 4 — Métriques de performance calculées à partir du résultat de
engine_vectorized.run_backtest().

Les clés du dict retourné par compute_metrics() correspondent exactement aux
colonnes de la table SQLite `backtest_results` (voir
packages/data-pipeline/init_db.py) — pensé pour une insertion directe au
Sprint 5, une fois l'API en place.

Sharpe/Sortino annualisés sur la base de 252 jours de bourse — hypothèse
correcte pour les actifs qui suivent le calendrier boursier (actions,
indices, forex, commodities). Pour la crypto (marché 24/7), ce chiffre
sous-estime légèrement le ratio annualisé réel ; un ajustement par classe
d'actif est prévu comme amélioration future si besoin (walk-forward,
Sprint 6).
"""
import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def compute_metrics(
    equity_curve: pd.DataFrame,
    trades: list,
    initial_capital: float,
    risk_free_rate: float = 0.0,
) -> dict:
    """
    equity_curve : DataFrame `timestamp`, `equity` (sortie de run_backtest).
    trades : liste de dicts avec au moins la clé `pnl` (sortie de
        run_backtest).
    risk_free_rate : taux sans risque annuel, en fraction (0.02 = 2 %).
    """
    equity = equity_curve["equity"].to_numpy(dtype=np.float64)
    final_equity = float(equity[-1]) if len(equity) else initial_capital

    returns = pd.Series(equity).pct_change().dropna().to_numpy()
    daily_rf = risk_free_rate / TRADING_DAYS_PER_YEAR

    if len(returns) > 1 and returns.std(ddof=1) > 0:
        sharpe = float(
            (returns.mean() - daily_rf) / returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
    else:
        sharpe = 0.0

    downside = returns[returns < 0]
    if len(downside) > 1 and downside.std(ddof=1) > 0:
        sortino = float(
            (returns.mean() - daily_rf) / downside.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        )
    else:
        sortino = 0.0

    if len(equity):
        running_max = np.maximum.accumulate(equity)
        drawdown = (equity - running_max) / running_max
        max_drawdown = float(drawdown.min())
    else:
        max_drawdown = 0.0

    pnls = np.array([t["pnl"] for t in trades], dtype=np.float64)
    total_trades = len(pnls)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    win_rate = float(len(wins) / total_trades) if total_trades else 0.0
    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0

    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    return {
        "final_equity": final_equity,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "total_trades": total_trades,
    }