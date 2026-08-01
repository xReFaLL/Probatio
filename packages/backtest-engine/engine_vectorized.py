"""
Sprint 4 — Moteur de backtest vectorisé (mode "prototypage rapide").

Étant donné une série de prix (OHLCV) et une série de positions désirées
(0/1 long-only pour les stratégies de référence, -1/0/1 plus généralement)
alignée sur les mêmes barres, calcule la courbe d'équité et reconstitue la
liste des trades individuels.

Décisions de modélisation (volontairement simplifiées pour ce mode — le
moteur event-driven du Sprint 6 fera une simulation d'ordres plus réaliste) :
  - Le signal calculé à la clôture de la barre t est exécuté à la barre t+1
    (décalage d'une barre), pour éviter tout biais d'anticipation.
  - Commission + slippage sont un coût proportionnel unique, appliqué à
    chaque changement de position (pas de carnet d'ordres, pas d'exécution
    partielle, pas de sizing dynamique — quantité fixe à 1 unité).

Ce moteur ne fait AUCUN appel réseau ni disque : il consomme exclusivement
des DataFrames déjà chargés (voir warehouse_reader.load_ohlcv), conformément
au principe du brief : le moteur ne lit jamais les APIs directement.
"""
import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _extract_trades(prices, positions, quantity):
    """
    Parcourt la série de positions exécutées et repère chaque changement
    pour reconstituer les trades individuels. Boucle séquentielle par nature
    (état "position en cours") -> numba plutôt que pandas pur, pour la
    vitesse sur de longs historiques (dizaines de milliers de barres/symbole
    une fois multiplié par des centaines de symboles).

    Retourne des tableaux parallèles (indices positionnels dans `prices`) :
    entry_idx, exit_idx, side (1=long, -1=short), entry_price, exit_price,
    pnl. Une position encore ouverte à la fin de la série est clôturée au
    dernier prix disponible (mark-to-market), pour ne perdre aucun trade en
    cours dans les métriques.
    """
    n = len(positions)
    entry_idx = np.empty(n, dtype=np.int64)
    exit_idx = np.empty(n, dtype=np.int64)
    side = np.empty(n, dtype=np.int64)
    entry_price = np.empty(n, dtype=np.float64)
    exit_price = np.empty(n, dtype=np.float64)
    pnl = np.empty(n, dtype=np.float64)

    n_trades = 0
    current_side = 0
    current_entry_idx = -1

    for i in range(n):
        pos = positions[i]
        if pos != current_side:
            if current_side != 0:
                entry_idx[n_trades] = current_entry_idx
                exit_idx[n_trades] = i
                side[n_trades] = current_side
                entry_price[n_trades] = prices[current_entry_idx]
                exit_price[n_trades] = prices[i]
                pnl[n_trades] = (prices[i] - prices[current_entry_idx]) * current_side * quantity
                n_trades += 1
            if pos != 0:
                current_entry_idx = i
            current_side = pos

    if current_side != 0:
        entry_idx[n_trades] = current_entry_idx
        exit_idx[n_trades] = n - 1
        side[n_trades] = current_side
        entry_price[n_trades] = prices[current_entry_idx]
        exit_price[n_trades] = prices[n - 1]
        pnl[n_trades] = (prices[n - 1] - prices[current_entry_idx]) * current_side * quantity
        n_trades += 1

    return (
        entry_idx[:n_trades], exit_idx[:n_trades], side[:n_trades],
        entry_price[:n_trades], exit_price[:n_trades], pnl[:n_trades],
    )


def run_backtest(
    df: pd.DataFrame,
    positions: pd.Series,
    initial_capital: float = 10_000.0,
    commission: float = 0.0005,
    slippage: float = 0.0005,
) -> dict:
    """
    df : DataFrame colonné `timestamp`, `close` (format warehouse_reader).
    positions : Series alignée sur df (même index), position désirée dans
        {-1, 0, 1} — le moteur applique lui-même le décalage d'une barre.
    commission, slippage : fractions (0.0005 = 5 points de base) appliquées
        à chaque changement de position, sur la valeur notionnelle.

    Retourne un dict :
      - equity_curve : DataFrame `timestamp`, `equity`
      - trades : liste de dicts au format de la table SQLite `trades`
        (entry_time, entry_price, exit_time, exit_price, quantity, side, pnl)
      - final_equity : capital final (float)
    """
    df = df.sort_values("timestamp").reset_index(drop=True)
    positions = positions.reindex(df.index).fillna(0)

    close = df["close"].to_numpy(dtype=np.float64)
    timestamps = df["timestamp"].to_numpy()
    pos = positions.to_numpy(dtype=np.int64)

    # Décalage d'une barre : le signal de clôture de t s'exécute à t+1.
    executed_pos = np.empty_like(pos)
    executed_pos[0] = 0
    executed_pos[1:] = pos[:-1]

    bar_returns = df["close"].pct_change().fillna(0).to_numpy()
    strategy_returns = executed_pos * bar_returns

    position_changes = np.abs(np.diff(executed_pos, prepend=0))
    strategy_returns = strategy_returns - position_changes * (commission + slippage)

    equity = initial_capital * np.cumprod(1 + strategy_returns)
    equity_curve = pd.DataFrame({"timestamp": timestamps, "equity": equity})

    quantity = 1.0  # sizing fixe — pas de dimensionnement par capital/risque au Sprint 4
    entry_idx, exit_idx, side, entry_price, exit_price, pnl = _extract_trades(
        close, executed_pos, quantity
    )

    trades = [
        {
            "entry_time": timestamps[entry_idx[i]],
            "entry_price": float(entry_price[i]),
            "exit_time": timestamps[exit_idx[i]],
            "exit_price": float(exit_price[i]),
            "quantity": quantity,
            "side": "long" if side[i] == 1 else "short",
            "pnl": float(pnl[i]),
        }
        for i in range(len(entry_idx))
    ]

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "final_equity": float(equity[-1]) if len(equity) else initial_capital,
    }