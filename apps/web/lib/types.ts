// Types miroir des schémas Pydantic de apps/api/schemas.py.
// Garder synchronisé manuellement avec le backend (pas de génération
// automatique pour l'instant — le projet est encore petit).

export type AssetClass = "equity" | "index" | "forex" | "commodity" | "crypto";
export type StrategyId = "sma_crossover" | "rsi_mean_reversion";

export interface Instrument {
  symbol: string;
  name: string;
  asset_class: AssetClass;
}

export interface OHLCVPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OHLCVResponse {
  symbol: string;
  asset_class: AssetClass;
  timeframe: string;
  points: OHLCVPoint[];
}

export interface BacktestRequest {
  symbol: string;
  asset_class: AssetClass;
  strategy: StrategyId;
  params: Record<string, number>;
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  commission: number;
  slippage: number;
}

export interface Trade {
  entry_time: string;
  entry_price: number;
  exit_time: string;
  exit_price: number;
  quantity: number;
  side: string;
  pnl: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
}

export interface Metrics {
  final_equity: number;
  sharpe: number;
  sortino: number;
  max_drawdown: number;
  win_rate: number;
  profit_factor: number | null;
  total_trades: number;
}

export interface BacktestResult {
  run_id: number;
  symbol: string;
  asset_class: AssetClass;
  strategy: StrategyId;
  params: Record<string, number>;
  start_date: string;
  end_date: string;
  initial_capital: number;
  metrics: Metrics;
  equity_curve: EquityPoint[];
  trades: Trade[];
}

export interface BacktestSummary {
  run_id: number;
  symbol: string;
  strategy: string;
  created_at: string;
  final_equity: number | null;
  sharpe: number | null;
  total_trades: number | null;
}

// Registre des stratégies côté client — doit rester en phase avec
// STRATEGY_REGISTRY dans apps/api/backtests.py (mêmes clés, mêmes valeurs
// par défaut). Utilisé pour générer dynamiquement le formulaire de
// paramètres sans aller-retour réseau.
export interface StrategyParamSpec {
  key: string;
  label: string;
  min: number;
  max: number;
  step: number;
}

export interface StrategySpec {
  id: StrategyId;
  label: string;
  params: StrategyParamSpec[];
}

export const STRATEGIES: StrategySpec[] = [
  {
    id: "sma_crossover",
    label: "Croisement de moyennes mobiles",
    params: [
      { key: "fast", label: "Moyenne rapide (jours)", min: 2, max: 100, step: 1 },
      { key: "slow", label: "Moyenne lente (jours)", min: 5, max: 300, step: 1 },
    ],
  },
  {
    id: "rsi_mean_reversion",
    label: "Retour à la moyenne (RSI)",
    params: [
      { key: "length", label: "Période RSI", min: 2, max: 60, step: 1 },
      { key: "oversold", label: "Seuil de survente", min: 5, max: 45, step: 1 },
      { key: "overbought", label: "Seuil de surachat", min: 55, max: 95, step: 1 },
    ],
  },
];

export const DEFAULT_PARAMS: Record<StrategyId, Record<string, number>> = {
  sma_crossover: { fast: 20, slow: 50 },
  rsi_mean_reversion: { length: 14, oversold: 30, overbought: 70 },
};