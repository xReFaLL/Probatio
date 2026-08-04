// Types miroir des schémas Pydantic de apps/api/schemas.py.
// Garder synchronisé manuellement avec le backend (pas de génération
// automatique pour l'instant — le projet est encore petit).

export type AssetClass = "equity" | "index" | "forex" | "commodity" | "crypto";
export type StrategyId = "sma_crossover" | "rsi_mean_reversion";
// Sprint 6 : deux moteurs interchangeables côté API (voir apps/api/backtests.py,
// ENGINE_REGISTRY) -- "vectorized" = Sprint 4 (rapide), "event_driven" =
// Sprint 6 (simulation d'ordres réaliste, sizing en %age du capital).
export type Engine = "vectorized" | "event_driven";

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
  engine: Engine;
  position_size: number;
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
  // `string` en plus de StrategyId : une stratégie custom (Sprint 7) renvoie
  // son nom libre choisi par l'utilisateur, pas un des deux ids internes.
  strategy: StrategyId | string;
  engine: Engine;
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

// --- Sprint 6 -- walk-forward analysis --------------------------------------

export interface WalkForwardRequest {
  symbol: string;
  asset_class: AssetClass;
  strategy: StrategyId;
  param_grid: Record<string, number[]>;
  start_date?: string;
  end_date?: string;
  in_sample_bars: number;
  out_sample_bars: number;
  step_bars?: number;
  optimize_metric: "sharpe" | "sortino" | "profit_factor" | "final_equity";
  initial_capital: number;
  commission: number;
  slippage: number;
  engine: Engine;
  position_size: number;
}

export interface WalkForwardWindow {
  window_index: number;
  is_start: string;
  is_end: string;
  oos_start: string;
  oos_end: string;
  best_params: Record<string, number>;
  is_score: number;
  oos_metrics: Metrics;
}

export interface WalkForwardResult {
  walk_forward_run_id: number;
  symbol: string;
  asset_class: AssetClass;
  strategy: string;
  optimize_metric: string;
  n_windows: number;
  windows: WalkForwardWindow[];
  aggregate_metrics: Metrics;
  stitched_equity_curve: EquityPoint[];
}

export interface WalkForwardSummary {
  walk_forward_run_id: number;
  symbol: string;
  strategy: string;
  created_at: string;
  n_windows: number | null;
  aggregate_sharpe: number | null;
}

// --- Sprint 6 -- screener ----------------------------------------------------

export type RankMetric =
  | "sharpe"
  | "sortino"
  | "final_equity"
  | "max_drawdown"
  | "win_rate"
  | "profit_factor"
  | "total_trades";

export interface ScreenerRequest {
  asset_class?: AssetClass;
  symbols?: string[];
  strategy: StrategyId;
  params: Record<string, number>;
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  commission: number;
  slippage: number;
  engine: Engine;
  position_size: number;
  rank_by: RankMetric;
}

export interface ScreenerResultItem {
  symbol: string;
  asset_class: AssetClass;
  metrics: Metrics;
}

export interface ScreenerSkipped {
  symbol: string;
  asset_class: AssetClass;
  reason: string;
}

export interface ScreenerResult {
  screener_run_id: number;
  strategy: string;
  params: Record<string, number>;
  rank_by: string;
  results: ScreenerResultItem[];
  skipped: ScreenerSkipped[];
}

export interface ScreenerSummary {
  screener_run_id: number;
  strategy: string;
  rank_by: string;
  created_at: string;
  n_results: number | null;
}

// --- Sprint 6 -- comparateur de stratégies -----------------------------------

export interface CompareVariantInput {
  label?: string;
  strategy: StrategyId;
  params: Record<string, number>;
  engine: Engine;
  position_size: number;
}

export interface CompareRequest {
  symbol: string;
  asset_class: AssetClass;
  variants: CompareVariantInput[];
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  commission: number;
  slippage: number;
}

export interface CompareVariantResult {
  label: string;
  run_id: number;
  strategy: string;
  params: Record<string, number>;
  engine: string;
  metrics: Metrics;
  equity_curve: EquityPoint[];
}

export interface CompareResult {
  symbol: string;
  asset_class: AssetClass;
  variants: CompareVariantResult[];
}

// --- Sprint 6 -- portefeuille multi-actifs -----------------------------------

export interface PortfolioLegInput {
  symbol: string;
  asset_class: AssetClass;
  strategy: StrategyId;
  params: Record<string, number>;
  weight: number;
}

export interface PortfolioRequest {
  name?: string;
  legs: PortfolioLegInput[];
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  commission: number;
  slippage: number;
  engine: Engine;
  position_size: number;
  rebalance: "none" | "monthly" | "quarterly";
}

export interface PortfolioLegResult {
  symbol: string;
  asset_class: AssetClass;
  strategy: string;
  params: Record<string, number>;
  weight: number;
  metrics: Metrics;
}

export interface PortfolioResult {
  portfolio_run_id: number;
  name?: string | null;
  rebalance: string;
  legs: PortfolioLegResult[];
  aggregate_metrics: Metrics;
  equity_curve: EquityPoint[];
}

export interface PortfolioSummary {
  portfolio_run_id: number;
  name?: string | null;
  created_at: string;
  final_equity: number | null;
  n_legs: number | null;
}


// --- Sprint 7 -- stratégies custom utilisateur --------------------------------
// Types miroir de apps/api/schemas.py (section "Sprint 7"). Voir aussi
// packages/backtest-engine/sandbox/ (exécution) et
// packages/data-pipeline/init_db.py (schéma strategy_code / strategy_execution_logs).

export type CustomStrategyMode = "vectorized" | "event_driven";

export interface CustomStrategyCodeVersion {
  id: number;
  mode: CustomStrategyMode;
  version: number;
  created_at: string;
}

export interface CustomStrategy {
  strategy_id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  versions: CustomStrategyCodeVersion[];
}

export interface CustomStrategySummary {
  strategy_id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  latest_version: number;
  latest_mode: CustomStrategyMode;
}

export interface CustomStrategyCreateRequest {
  name: string;
  description?: string;
  code: string;
  mode: CustomStrategyMode;
}

export interface CustomStrategyUpdateCodeRequest {
  code: string;
  mode: CustomStrategyMode;
}

export interface CustomStrategyTestRequest {
  code: string;
  mode: CustomStrategyMode;
  params: Record<string, number>;
  symbol: string;
  asset_class: AssetClass;
}

export type SandboxStatus = "ok" | "invalid" | "error" | "timeout";

export interface CustomStrategyTestResult {
  status: SandboxStatus;
  positions: number[];
  timestamps: string[];
  errors: string[];
  error?: string | null;
  traceback?: string | null;
  stdout: string;
  stderr: string;
  execution_time_ms: number;
}

export interface CustomStrategyBacktestRequest {
  symbol: string;
  asset_class: AssetClass;
  params: Record<string, number>;
  version?: number;
  start_date?: string;
  end_date?: string;
  initial_capital: number;
  commission: number;
  slippage: number;
  engine: Engine;
  position_size: number;
}

export interface ExecutionLog {
  id: number;
  run_id: number | null;
  version: number;
  kind: "quick_test" | "full_run";
  status: SandboxStatus;
  stdout?: string | null;
  stderr?: string | null;
  execution_time_ms?: number | null;
  created_at: string;
}

// Squelettes de départ affichés dans l'éditeur -- respectent le contrat
// documenté côté backend (voir sandbox/runner.py:_run_vectorized/_run_event_driven).
export const CUSTOM_STRATEGY_TEMPLATES: Record<CustomStrategyMode, string> = {
  vectorized: `def generate_signals(df, params):
    """
    df : DataFrame colonnes timestamp/open/high/low/close/volume.
    params : dict de paramètres passés depuis le formulaire.
    Retourne une pandas.Series alignée sur df, valeurs dans {-1, 0, 1}
    (position désirée -- le moteur applique lui-même le décalage d'une barre).
    """
    fast = df["close"].rolling(int(params.get("fast", 20))).mean()
    slow = df["close"].rolling(int(params.get("slow", 50))).mean()
    return (fast > slow).astype(int)
`,
  event_driven: `def on_bar(context, bar):
    """
    context.history : DataFrame de toutes les barres jusqu'à l'instant présent
        inclus (pas d'anticipation possible).
    context.index : position de la barre courante dans l'historique.
    context.state : dict libre pour garder de l'état d'une barre à l'autre.
    bar : la barre courante (Series -- open/high/low/close/volume/timestamp).
    Retourne un entier dans {-1, 0, 1} (position désirée pour cette barre).
    """
    if context.index < 50:
        return 0
    fast = context.history["close"].tail(20).mean()
    slow = context.history["close"].tail(50).mean()
    return 1 if fast > slow else 0
`,
};