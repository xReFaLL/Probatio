import type {
  AssetClass,
  BacktestRequest,
  BacktestResult,
  BacktestSummary,
  Instrument,
  OHLCVResponse,
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

export { ApiError };