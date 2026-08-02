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