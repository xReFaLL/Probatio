"use client";

import type { BacktestSummary } from "@/lib/types";
import { fmtCurrency, fmtDate, fmtNumber } from "@/lib/format";

interface Props {
  history: BacktestSummary[];
  activeRunId?: number;
  onSelect: (runId: number) => void;
}

export default function HistoryPanel({ history, activeRunId, onSelect }: Props) {
  return (
    <div className="rounded-lg border border-border bg-bg-panel">
      <h3 className="px-4 pt-4 text-xs font-semibold uppercase tracking-wide text-ink-muted">
        Historique des runs
      </h3>
      {history.length === 0 ? (
        <p className="p-4 text-sm text-ink-faint">Aucun backtest lancé pour l&apos;instant.</p>
      ) : (
        <ul className="max-h-[480px] overflow-y-auto p-2">
          {history.map((h) => (
            <li key={h.run_id}>
              <button
                onClick={() => onSelect(h.run_id)}
                className={`w-full rounded-md px-3 py-2 text-left text-sm transition hover:bg-bg-raised ${
                  activeRunId === h.run_id ? "bg-bg-raised ring-1 ring-signal/40" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-ink">{h.symbol}</span>
                  <span className="text-[11px] text-ink-faint">{fmtDate(h.created_at)}</span>
                </div>
                <div className="mt-0.5 flex items-center justify-between text-xs text-ink-muted">
                  <span>{h.strategy}</span>
                  <span className="tabular font-mono">
                    {h.final_equity != null ? fmtCurrency(h.final_equity) : "—"}
                    {h.sharpe != null ? ` · Sharpe ${fmtNumber(h.sharpe, 2)}` : ""}
                  </span>
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}