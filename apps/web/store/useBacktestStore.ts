import { create } from "zustand";
import type { BacktestResult, BacktestSummary, OHLCVResponse } from "@/lib/types";

interface BacktestStore {
  result: BacktestResult | null;
  ohlcv: OHLCVResponse | null;
  history: BacktestSummary[];
  isRunning: boolean;
  error: string | null;

  setResult: (result: BacktestResult | null) => void;
  setOhlcv: (ohlcv: OHLCVResponse | null) => void;
  setHistory: (history: BacktestSummary[]) => void;
  prependHistory: (summary: BacktestSummary) => void;
  setRunning: (running: boolean) => void;
  setError: (error: string | null) => void;
}

// Store volontairement plat : le projet n'a qu'une poignée de composants qui
// ont besoin de partager le résultat courant (graphique de prix, courbe
// d'equity, panneau de métriques, table des trades, historique) sans passer
// par un prop-drilling profond depuis app/page.tsx.
export const useBacktestStore = create<BacktestStore>((set) => ({
  result: null,
  ohlcv: null,
  history: [],
  isRunning: false,
  error: null,

  setResult: (result) => set({ result }),
  setOhlcv: (ohlcv) => set({ ohlcv }),
  setHistory: (history) => set({ history }),
  prependHistory: (summary) =>
    set((state) => ({ history: [summary, ...state.history].slice(0, 50) })),
  setRunning: (isRunning) => set({ isRunning }),
  setError: (error) => set({ error }),
}));