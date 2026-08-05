"""
Sprint 4 — Stratégies de référence, pour valider le moteur de backtest.

Chaque fonction prend un DataFrame OHLCV (format warehouse_reader.load_ohlcv,
colonne `timestamp`, index RangeIndex) et retourne une Series de position
désirée alignée sur le même index, valeurs dans {0, 1} (long-only pour ces
deux références — pas de position courte). Le résultat se passe tel quel à
engine_vectorized.run_backtest().
"""
import pandas as pd

from indicators import sma, rsi


def sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50) -> pd.Series:
    """
    Croisement de moyennes mobiles simples — suivi de tendance classique.
    Position longue tant que la moyenne rapide est au-dessus de la moyenne
    lente, flat sinon (état, pas juste l'instant du croisement).
    """
    fast_ma = sma(df, length=fast)
    slow_ma = sma(df, length=slow)
    return (fast_ma > slow_ma).astype(int)


def rsi_mean_reversion(
    df: pd.DataFrame, length: int = 14, oversold: int = 30, overbought: int = 70
) -> pd.Series:
    """
    Retour à la moyenne basé sur le RSI — entre en position longue quand le
    RSI ressort de la zone de survente (croisement à la hausse du seuil
    `oversold`), sort quand il entre en zone de surachat (croisement à la
    hausse du seuil `overbought`). Reste en position entre les deux signaux.
    """
    r = rsi(df, length=length)

    enter = (r.shift(1) <= oversold) & (r > oversold)
    exit_ = (r.shift(1) < overbought) & (r >= overbought)

    signal = pd.Series(pd.NA, index=r.index, dtype="Int64")
    signal[enter] = 1
    signal[exit_] = 0
    signal = signal.ffill().fillna(0)

    return signal.astype(int)