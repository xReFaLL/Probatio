"""Wrapper autour de pandas-ta-classic (indicateurs techniques). On appelle
les fonctions "core" directement sur une Series plutôt que l'accesseur
`df.ta.xxx()`, pour rester explicite sur la colonne utilisée."""
import pandas as pd
import pandas_ta_classic as ta


def sma(df: pd.DataFrame, length: int = 20, column: str = "close") -> pd.Series:
    """Moyenne mobile simple."""
    return ta.sma(df[column], length=length)


def ema(df: pd.DataFrame, length: int = 20, column: str = "close") -> pd.Series:
    """Moyenne mobile exponentielle."""
    return ta.ema(df[column], length=length)


def rsi(df: pd.DataFrame, length: int = 14, column: str = "close") -> pd.Series:
    """Relative Strength Index (0-100)."""
    return ta.rsi(df[column], length=length)