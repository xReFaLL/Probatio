"""
Sprint 5 — Modèles Pydantic (requêtes/réponses de l'API).
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field


class InstrumentOut(BaseModel):
    symbol: str
    name: str
    asset_class: str


class BacktestRequest(BaseModel):
    symbol: str
    asset_class: Literal["equity", "index", "forex", "commodity", "crypto"]
    strategy: Literal["sma_crossover", "rsi_mean_reversion"]
    params: dict = Field(default_factory=dict)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    slippage: float = 0.0005
    # Sprint 6 : choix du moteur. "vectorized" = Sprint 4 (rapide, prototypage),
    # "event_driven" = Sprint 6 (simulation d'ordres réaliste, sizing en % du
    # capital, equity mark-to-market à chaque barre — voir engine_event_driven.py).
    engine: Literal["vectorized", "event_driven"] = "vectorized"
    position_size: float = Field(
        default=1.0,
        description="Fraction du capital disponible allouée à chaque position, "
                     "utilisée uniquement par le moteur event_driven.",
    )


class TradeOut(BaseModel):
    entry_time: str
    entry_price: float
    exit_time: str
    exit_price: float
    quantity: float
    side: str
    pnl: float


class EquityPointOut(BaseModel):
    timestamp: str
    equity: float


class MetricsOut(BaseModel):
    final_equity: float
    sharpe: float
    sortino: float
    max_drawdown: float
    win_rate: float
    profit_factor: Optional[float] = None  # None = pas de trade perdant (profit factor infini)
    total_trades: int


class BacktestResultOut(BaseModel):
    run_id: int
    symbol: str
    asset_class: str
    strategy: str
    engine: str = "vectorized"
    params: dict
    start_date: str
    end_date: str
    initial_capital: float
    metrics: MetricsOut
    equity_curve: list[EquityPointOut]
    trades: list[TradeOut]


class BacktestSummaryOut(BaseModel):
    run_id: int
    symbol: str
    strategy: str
    created_at: str
    final_equity: Optional[float] = None
    sharpe: Optional[float] = None
    total_trades: Optional[int] = None


# --- Sprint 5 (partie 2) — ajouté pour le graphique de prix du frontend ---
# Le moteur/l'entrepôt n'exposaient jusqu'ici les OHLCV qu'en interne
# (warehouse_reader.load_ohlcv, package backtest-engine). On réutilise
# exactement cette fonction ici : aucune nouvelle lecture de données, juste
# une sérialisation JSON de ce qui existe déjà, pour alimenter le graphique
# TradingView Lightweight Charts côté web.

class OHLCVPointOut(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVResponseOut(BaseModel):
    symbol: str
    asset_class: str
    timeframe: str
    points: list[OHLCVPointOut]


# --- Sprint 6 -- walk-forward analysis --------------------------------------
# Voir packages/backtest-engine/walk_forward.py pour la logique. Ces modèles
# sérialisent tels quels le dict retourné par run_walk_forward().

class WalkForwardRequest(BaseModel):
    symbol: str
    asset_class: Literal["equity", "index", "forex", "commodity", "crypto"]
    strategy: Literal["sma_crossover", "rsi_mean_reversion"]
    # Valeurs scalaires ou listes -> grille testée par produit cartésien,
    # ex. {"fast": [10, 20], "slow": [50, 100]} teste les 4 combinaisons.
    param_grid: dict = Field(default_factory=dict)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    in_sample_bars: int = Field(default=504, gt=0)
    out_sample_bars: int = Field(default=126, gt=0)
    step_bars: Optional[int] = Field(default=None, gt=0)
    optimize_metric: Literal["sharpe", "sortino", "profit_factor", "final_equity"] = "sharpe"
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    slippage: float = 0.0005
    engine: Literal["vectorized", "event_driven"] = "vectorized"
    position_size: float = 1.0


class WalkForwardWindowOut(BaseModel):
    window_index: int
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str
    best_params: dict
    is_score: float
    oos_metrics: MetricsOut


class WalkForwardResultOut(BaseModel):
    walk_forward_run_id: int
    symbol: str
    asset_class: str
    strategy: str
    optimize_metric: str
    n_windows: int
    windows: list[WalkForwardWindowOut]
    aggregate_metrics: MetricsOut
    stitched_equity_curve: list[EquityPointOut]


class WalkForwardSummaryOut(BaseModel):
    walk_forward_run_id: int
    symbol: str
    strategy: str
    created_at: str
    n_windows: Optional[int] = None
    aggregate_sharpe: Optional[float] = None


# --- Sprint 6 -- screener ----------------------------------------------------

class ScreenerRequest(BaseModel):
    asset_class: Optional[Literal["equity", "index", "forex", "commodity", "crypto"]] = None
    # Si symbols est omis, scanne tout l'univers disponible pour asset_class
    # (ou tout l'univers disponible tout court si asset_class est aussi omis).
    symbols: Optional[list[str]] = None
    strategy: Literal["sma_crossover", "rsi_mean_reversion"]
    params: dict = Field(default_factory=dict)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    slippage: float = 0.0005
    engine: Literal["vectorized", "event_driven"] = "vectorized"
    position_size: float = 1.0
    rank_by: Literal[
        "sharpe", "sortino", "final_equity", "max_drawdown", "win_rate", "profit_factor", "total_trades"
    ] = "sharpe"


class ScreenerResultItemOut(BaseModel):
    symbol: str
    asset_class: str
    metrics: MetricsOut


class ScreenerSkippedOut(BaseModel):
    symbol: str
    asset_class: str
    reason: str


class ScreenerResultOut(BaseModel):
    screener_run_id: int
    strategy: str
    params: dict
    rank_by: str
    results: list[ScreenerResultItemOut]
    skipped: list[ScreenerSkippedOut]


class ScreenerSummaryOut(BaseModel):
    screener_run_id: int
    strategy: str
    rank_by: str
    created_at: str
    n_results: Optional[int] = None


# --- Sprint 6 -- comparateur de stratégies -----------------------------------
# Orchestration légère au-dessus de /backtests : pas de nouvelle table SQLite,
# chaque variante est un backtest complet et déjà persisté normalement
# (voir apps/api/compare.py, qui réutilise apps/api/backtests.py).

class CompareVariantIn(BaseModel):
    label: Optional[str] = None
    strategy: Literal["sma_crossover", "rsi_mean_reversion"]
    params: dict = Field(default_factory=dict)
    engine: Literal["vectorized", "event_driven"] = "vectorized"
    position_size: float = 1.0


class CompareRequest(BaseModel):
    symbol: str
    asset_class: Literal["equity", "index", "forex", "commodity", "crypto"]
    variants: list[CompareVariantIn] = Field(min_length=1, max_length=8)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    slippage: float = 0.0005


class CompareVariantResultOut(BaseModel):
    label: str
    run_id: int
    strategy: str
    params: dict
    engine: str
    metrics: MetricsOut
    equity_curve: list[EquityPointOut]


class CompareResultOut(BaseModel):
    symbol: str
    asset_class: str
    variants: list[CompareVariantResultOut]


# --- Sprint 6 -- portefeuille multi-actifs -----------------------------------

class PortfolioLegIn(BaseModel):
    symbol: str
    asset_class: Literal["equity", "index", "forex", "commodity", "crypto"]
    strategy: Literal["sma_crossover", "rsi_mean_reversion"]
    params: dict = Field(default_factory=dict)
    weight: float = Field(default=1.0, gt=0)


class PortfolioRequest(BaseModel):
    name: Optional[str] = None
    legs: list[PortfolioLegIn] = Field(min_length=1)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    initial_capital: float = 10_000.0
    commission: float = 0.0005
    slippage: float = 0.0005
    engine: Literal["vectorized", "event_driven"] = "vectorized"
    position_size: float = 1.0
    rebalance: Literal["none", "monthly", "quarterly"] = "none"


class PortfolioLegResultOut(BaseModel):
    symbol: str
    asset_class: str
    strategy: str
    params: dict
    weight: float
    metrics: MetricsOut


class PortfolioResultOut(BaseModel):
    portfolio_run_id: int
    name: Optional[str] = None
    rebalance: str
    legs: list[PortfolioLegResultOut]
    aggregate_metrics: MetricsOut
    equity_curve: list[EquityPointOut]


class PortfolioSummaryOut(BaseModel):
    portfolio_run_id: int
    name: Optional[str] = None
    created_at: str
    final_equity: Optional[float] = None
    n_legs: Optional[int] = None