import type {
  AssetClass,
  BacktestRequest,
  BacktestResult,
  BacktestSummary,
  CompareRequest,
  CompareResult,
  CustomStrategy,
  CustomStrategyBacktestRequest,
  CustomStrategyCreateRequest,
  CustomStrategySummary,
  CustomStrategyTestRequest,
  CustomStrategyTestResult,
  CustomStrategyUpdateCodeRequest,
  ExecutionLog,
  Instrument,
  OHLCVResponse,
  PortfolioRequest,
  PortfolioResult,
  PortfolioSummary,
  ScreenerRequest,
  ScreenerResult,
  ScreenerSummary,
  WalkForwardRequest,
  WalkForwardResult,
  WalkForwardSummary,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      `Impossible de joindre l'API sur ${API_URL}. Vérifie que \`uvicorn apps.api.main:app\` tourne bien.`
    );
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // pas de corps JSON exploitable, on garde statusText
    }
    throw new ApiError(res.status, detail);
  }

  return res.json() as Promise<T>;
}

export function getInstruments(): Promise<Instrument[]> {
  return request<Instrument[]>("/api/instruments");
}

export function getOhlcv(
  symbol: string,
  assetClass: AssetClass,
  start?: string,
  end?: string
): Promise<OHLCVResponse> {
  const qs = new URLSearchParams({ asset_class: assetClass });
  if (start) qs.set("start", start);
  if (end) qs.set("end", end);
  return request<OHLCVResponse>(`/api/instruments/${encodeURIComponent(symbol)}/ohlcv?${qs}`);
}

export function runBacktest(req: BacktestRequest): Promise<BacktestResult> {
  return request<BacktestResult>("/api/backtests", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listBacktests(limit = 50): Promise<BacktestSummary[]> {
  return request<BacktestSummary[]>(`/api/backtests?limit=${limit}`);
}

export function getBacktest(runId: number): Promise<BacktestResult> {
  return request<BacktestResult>(`/api/backtests/${runId}`);
}

// --- Sprint 6 -- walk-forward analysis --------------------------------------

export function runWalkForward(req: WalkForwardRequest): Promise<WalkForwardResult> {
  return request<WalkForwardResult>("/api/walk-forward", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listWalkForwards(limit = 50): Promise<WalkForwardSummary[]> {
  return request<WalkForwardSummary[]>(`/api/walk-forward?limit=${limit}`);
}

export function getWalkForward(id: number): Promise<WalkForwardResult> {
  return request<WalkForwardResult>(`/api/walk-forward/${id}`);
}

// --- Sprint 6 -- screener ----------------------------------------------------

export function runScreener(req: ScreenerRequest): Promise<ScreenerResult> {
  return request<ScreenerResult>("/api/screener", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listScreeners(limit = 50): Promise<ScreenerSummary[]> {
  return request<ScreenerSummary[]>(`/api/screener?limit=${limit}`);
}

export function getScreener(id: number): Promise<ScreenerResult> {
  return request<ScreenerResult>(`/api/screener/${id}`);
}

// --- Sprint 6 -- comparateur de stratégies -----------------------------------

export function runCompare(req: CompareRequest): Promise<CompareResult> {
  return request<CompareResult>("/api/compare", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// --- Sprint 6 -- portefeuille multi-actifs -----------------------------------

export function runPortfolio(req: PortfolioRequest): Promise<PortfolioResult> {
  return request<PortfolioResult>("/api/portfolio", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listPortfolios(limit = 50): Promise<PortfolioSummary[]> {
  return request<PortfolioSummary[]>(`/api/portfolio?limit=${limit}`);
}

export function getPortfolio(id: number): Promise<PortfolioResult> {
  return request<PortfolioResult>(`/api/portfolio/${id}`);
}


// --- Sprint 7 -- stratégies custom utilisateur --------------------------------

export function createCustomStrategy(req: CustomStrategyCreateRequest): Promise<CustomStrategy> {
  return request<CustomStrategy>("/api/custom-strategies", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listCustomStrategies(limit = 50): Promise<CustomStrategySummary[]> {
  return request<CustomStrategySummary[]>(`/api/custom-strategies?limit=${limit}`);
}

export function getCustomStrategy(id: number): Promise<CustomStrategy> {
  return request<CustomStrategy>(`/api/custom-strategies/${id}`);
}

export function addCustomStrategyVersion(
  id: number,
  req: CustomStrategyUpdateCodeRequest
): Promise<CustomStrategy> {
  return request<CustomStrategy>(`/api/custom-strategies/${id}/versions`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// Test rapide sur échantillon réduit -- code fourni directement, pas besoin
// d'avoir sauvegardé la stratégie au préalable (retour immédiat pendant l'édition).
export function testCustomStrategy(req: CustomStrategyTestRequest): Promise<CustomStrategyTestResult> {
  return request<CustomStrategyTestResult>("/api/custom-strategies/test", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function backtestCustomStrategy(
  id: number,
  req: CustomStrategyBacktestRequest
): Promise<BacktestResult> {
  return request<BacktestResult>(`/api/custom-strategies/${id}/backtest`, {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function listCustomStrategyLogs(id: number, limit = 20): Promise<ExecutionLog[]> {
  return request<ExecutionLog[]>(`/api/custom-strategies/${id}/logs?limit=${limit}`);
}

export { ApiError };