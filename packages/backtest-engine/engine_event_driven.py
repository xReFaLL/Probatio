"""Placeholder — implémenté au Sprint 4 (vectorisé) ou Sprint 6 (event-driven)."""
"""
Sprint 6 — Moteur de backtest event-driven (mode "validation réaliste").

Contrairement à engine_vectorized.run_backtest, qui approxime la performance
par un produit cumulé de rendements barre-à-barre (rapide, mais insensible
au sizing réel et au coût exact d'exécution), ce moteur simule des ordres
individuels :
  - le signal calculé à la clôture de la barre t est toujours exécuté à la
    barre t+1 (même convention que le moteur vectorisé, pour rester
    comparable et éviter tout biais d'anticipation) ;
  - l'exécution se fait à l'*open* de la barre t+1, ajusté par le slippage
    dans le sens défavorable (achat plus cher, vente moins chère) ;
  - la commission est calculée sur la valeur notionnelle réelle de chaque
    ordre (pas une approximation par rendement) ;
  - le sizing est un pourcentage du capital disponible (`position_size`,
    défaut 1.0 = 100% du cash disponible au moment de l'entrée) plutôt
    qu'une quantité fixe à 1 unité comme au Sprint 4 — plus réaliste pour
    comparer des instruments à des prix très différents (ex. BTC vs EURUSD) ;
  - l'equity est mark-to-market à *chaque* barre (close), pas seulement aux
    changements de position — la courbe reflète donc aussi les gains/pertes
    latents d'une position encore ouverte, contrairement au Sprint 4.

Signature d'entrée/sortie volontairement identique à
engine_vectorized.run_backtest (mêmes clés de retour : equity_curve, trades,
final_equity) pour rester interchangeable côté API (voir apps/api/backtests.py,
paramètre `engine`) et compatible telle quelle avec metrics.compute_metrics
et les fonctions d'insertion SQLite de apps/api/db.py.

Comme le moteur vectorisé, aucun accès réseau/disque ici : uniquement des
DataFrames déjà chargés via warehouse_reader.load_ohlcv.
"""
import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _simulate(open_, close, executed_pos, initial_capital, commission, slippage, position_size):
    """
    Boucle bar-by-bar : maintient cash + quantité de position (signée,
    positive = long, négative = short), exécute les changements de position
    à l'open de la barre courante, marque l'equity au close de chaque barre.

    Retourne :
      equity (float64[n]) — equity mark-to-market à chaque barre
      entry_idx, exit_idx, side, entry_price, exit_price, quantity, pnl,
      commission_paid — tableaux parallèles décrivant chaque trade clôturé
      (même convention que engine_vectorized._extract_trades : une position
      encore ouverte à la fin de la série est clôturée au dernier close
      disponible, pour le reporting — cela n'affecte pas la simulation de
      cash/equity elle-même, déjà mark-to-market jusqu'à la dernière barre).
    """
    n = len(executed_pos)
    equity = np.empty(n, dtype=np.float64)

    entry_idx = np.empty(n, dtype=np.int64)
    exit_idx = np.empty(n, dtype=np.int64)
    side = np.empty(n, dtype=np.int64)
    entry_price = np.empty(n, dtype=np.float64)
    exit_price = np.empty(n, dtype=np.float64)
    quantity = np.empty(n, dtype=np.float64)
    pnl = np.empty(n, dtype=np.float64)
    commission_paid = np.empty(n, dtype=np.float64)

    n_trades = 0
    cash = initial_capital
    position_qty = 0.0
    current_side = 0
    current_entry_idx = -1
    current_entry_price = 0.0

    for t in range(n):
        desired = executed_pos[t]

        if desired != current_side:
            fill_base = open_[t]

            # Clôture de la position en cours, s'il y en a une.
            if current_side != 0:
                if current_side > 0:
                    close_fill = fill_base * (1.0 - slippage)  # vente -> prix défavorable = plus bas
                else:
                    close_fill = fill_base * (1.0 + slippage)  # rachat -> prix défavorable = plus haut

                proceeds = position_qty * close_fill
                comm_cost = abs(position_qty * close_fill) * commission
                cash += proceeds - comm_cost

                entry_idx[n_trades] = current_entry_idx
                exit_idx[n_trades] = t
                side[n_trades] = current_side
                entry_price[n_trades] = current_entry_price
                exit_price[n_trades] = close_fill
                quantity[n_trades] = abs(position_qty)
                pnl[n_trades] = (close_fill - current_entry_price) * position_qty - comm_cost
                commission_paid[n_trades] = comm_cost
                n_trades += 1

                position_qty = 0.0

            # Ouverture de la nouvelle position désirée, sizée en %age du cash disponible.
            if desired != 0:
                if desired > 0:
                    open_fill = fill_base * (1.0 + slippage)  # achat -> prix défavorable = plus haut
                else:
                    open_fill = fill_base * (1.0 - slippage)  # vente à découvert -> prix défavorable = plus bas

                notional = cash * position_size
                new_qty = (notional / open_fill) * (1.0 if desired > 0 else -1.0)
                comm_cost = abs(new_qty * open_fill) * commission
                cash -= new_qty * open_fill + comm_cost

                position_qty = new_qty
                current_entry_idx = t
                current_entry_price = open_fill

            current_side = desired

        equity[t] = cash + position_qty * close[t]

    # Position encore ouverte en fin de série -> clôturée au dernier close
    # pour le reporting des trades (n'affecte pas equity, déjà marquée ci-dessus).
    if current_side != 0:
        last_price = close[n - 1]
        comm_cost = abs(position_qty * last_price) * commission
        entry_idx[n_trades] = current_entry_idx
        exit_idx[n_trades] = n - 1
        side[n_trades] = current_side
        entry_price[n_trades] = current_entry_price
        exit_price[n_trades] = last_price
        quantity[n_trades] = abs(position_qty)
        pnl[n_trades] = (last_price - current_entry_price) * position_qty - comm_cost
        commission_paid[n_trades] = comm_cost
        n_trades += 1

    return (
        equity,
        entry_idx[:n_trades], exit_idx[:n_trades], side[:n_trades],
        entry_price[:n_trades], exit_price[:n_trades], quantity[:n_trades],
        pnl[:n_trades], commission_paid[:n_trades],
    )


def run_backtest(
    df: pd.DataFrame,
    positions: pd.Series,
    initial_capital: float = 10_000.0,
    commission: float = 0.0005,
    slippage: float = 0.0005,
    position_size: float = 1.0,
) -> dict:
    """
    df : DataFrame colonné `timestamp`, `open`, `close` (format
        warehouse_reader.load_ohlcv).
    positions : Series alignée sur df, position désirée dans {-1, 0, 1} — le
        moteur applique lui-même le décalage d'une barre (comme au Sprint 4).
    position_size : fraction du cash disponible allouée à chaque nouvelle
        position (1.0 = 100%, pas de levier ; <1.0 pour garder une marge de
        cash ; le moteur ne plafonne pas au-delà de 1.0, un levier > 1 est
        possible mais à la charge de l'appelant de le justifier).

    Retourne un dict au même format que engine_vectorized.run_backtest :
      - equity_curve : DataFrame `timestamp`, `equity` (mark-to-market à
        chaque barre, contrairement au Sprint 4)
      - trades : liste de dicts (entry_time, entry_price, exit_time,
        exit_price, quantity, side, pnl, commission — champ additionnel,
        ignoré sans erreur par les fonctions d'insertion SQLite existantes)
      - final_equity : capital final (float)
    """
    if position_size <= 0:
        raise ValueError("position_size doit être strictement positif.")

    df = df.sort_values("timestamp").reset_index(drop=True)
    positions = positions.reindex(df.index).fillna(0)

    open_ = df["open"].to_numpy(dtype=np.float64)
    close = df["close"].to_numpy(dtype=np.float64)
    timestamps = df["timestamp"].to_numpy()
    pos = positions.to_numpy(dtype=np.int64)

    executed_pos = np.empty_like(pos)
    executed_pos[0] = 0
    executed_pos[1:] = pos[:-1]

    (
        equity, entry_idx, exit_idx, side, entry_price, exit_price,
        quantity, pnl, commission_paid,
    ) = _simulate(open_, close, executed_pos, initial_capital, commission, slippage, position_size)

    equity_curve = pd.DataFrame({"timestamp": timestamps, "equity": equity})

    trades = [
        {
            "entry_time": timestamps[entry_idx[i]],
            "entry_price": float(entry_price[i]),
            "exit_time": timestamps[exit_idx[i]],
            "exit_price": float(exit_price[i]),
            "quantity": float(quantity[i]),
            "side": "long" if side[i] == 1 else "short",
            "pnl": float(pnl[i]),
            "commission": float(commission_paid[i]),
        }
        for i in range(len(entry_idx))
    ]

    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "final_equity": float(equity[-1]) if len(equity) else initial_capital,
    }